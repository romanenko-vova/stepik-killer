import json

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert

from db.database import as_dict, get_session
from db.models import PersonalSet, PersonalSetAccess, Solution, Task, User
from db.seed import content_sig


def normalize_tests(inputs: list[str], expecteds: list[str]) -> list[dict]:
    # пустую пару пропускаем — это просто незаполненная строка формы
    tests = []
    count = max(len(inputs), len(expecteds))
    for i in range(count):
        raw_in = inputs[i] if i < len(inputs) else ""
        raw_out = expecteds[i] if i < len(expecteds) else ""
        inp = raw_in.replace("\r\n", "\n").strip()
        exp = raw_out.replace("\r\n", "\n").strip()
        if inp == "" and exp == "":
            continue
        tests.append({"input": inp, "expected": exp})
    return tests


async def sets_for_user(user_id: int) -> list[dict]:
    async with get_session() as session:
        rows = (
            await session.execute(
                select(PersonalSet)
                .join(PersonalSetAccess, PersonalSetAccess.set_id == PersonalSet.id)
                .where(PersonalSetAccess.user_id == user_id)
                .order_by(PersonalSet.id)
            )
        ).scalars().all()
        return [as_dict(row) for row in rows]


async def all_sets() -> list[dict]:
    task_count = (
        select(func.count()).select_from(Task).where(Task.set_id == PersonalSet.id).scalar_subquery()
    )
    async with get_session() as session:
        rows = await session.execute(
            select(
                PersonalSet,
                User.first_name,
                User.username,
                User.id_tg,
                task_count.label("task_count"),
            )
            .join(User, User.id == PersonalSet.user_id)
            .order_by(PersonalSet.id.desc())
        )
        out = []
        for personal, first_name, username, id_tg, count in rows:
            item = as_dict(personal)
            item.update(first_name=first_name, username=username, id_tg=id_tg, task_count=count)
            out.append(item)
        return out


async def get_set(set_id: int) -> dict | None:
    async with get_session() as session:
        return as_dict(await session.get(PersonalSet, set_id))


async def grant_access(set_id: int, user_id: int):
    async with get_session() as session:
        await session.execute(
            insert(PersonalSetAccess).values(set_id=set_id, user_id=user_id).on_conflict_do_nothing()
        )
        await session.commit()


async def user_can_see_set(user_id: int, set_id: int) -> bool:
    async with get_session() as session:
        row = await session.execute(
            select(PersonalSetAccess.set_id).where(
                PersonalSetAccess.set_id == set_id, PersonalSetAccess.user_id == user_id
            )
        )
        return row.first() is not None


async def find_set_by_title(user_id: int, title: str) -> dict | None:
    async with get_session() as session:
        row = (
            await session.execute(
                select(PersonalSet).where(PersonalSet.user_id == user_id, PersonalSet.title == title)
            )
        ).scalars().first()
        return as_dict(row)


async def create_set(user_id: int, title: str) -> int:
    async with get_session() as session:
        personal = PersonalSet(user_id=user_id, title=title)
        session.add(personal)
        await session.flush()
        await session.execute(
            insert(PersonalSetAccess)
            .values(set_id=personal.id, user_id=user_id)
            .on_conflict_do_nothing()
        )
        await session.commit()
        return personal.id


async def update_set_title(set_id: int, title: str):
    async with get_session() as session:
        await session.execute(update(PersonalSet).where(PersonalSet.id == set_id).values(title=title))
        # в карточке решения тема берётся из tasks.topic
        await session.execute(update(Task).where(Task.set_id == set_id).values(topic=title))
        await session.commit()


async def delete_set(set_id: int):
    async with get_session() as session:
        task_ids = select(Task.id).where(Task.set_id == set_id)
        await session.execute(delete(Solution).where(Solution.task_id.in_(task_ids)))
        await session.execute(delete(Task).where(Task.set_id == set_id))
        await session.execute(delete(PersonalSetAccess).where(PersonalSetAccess.set_id == set_id))
        await session.execute(delete(PersonalSet).where(PersonalSet.id == set_id))
        await session.commit()


async def tasks_in_set(set_id: int) -> list[dict]:
    async with get_session() as session:
        rows = (
            await session.execute(
                select(Task)
                .where(Task.set_id == set_id)
                .order_by(func.coalesce(Task.pos, Task.id), Task.id)
            )
        ).scalars().all()
        return [as_dict(row) for row in rows]


def task_status_columns(user_id: int):
    """Подзапросы «сколько попыток / когда последняя / решена ли» по задаче для ученика."""
    mine = (Solution.user_id == user_id) & (Solution.task_id == Task.id)
    attempts = select(func.count()).select_from(Solution).where(mine).scalar_subquery()
    last_try = (
        select(Solution.created_at).where(mine).order_by(Solution.id.desc()).limit(1).scalar_subquery()
    )
    last_status = (
        select(Solution.status).where(mine).order_by(Solution.id.desc()).limit(1).scalar_subquery()
    )
    current_ok = exists().where(
        mine,
        Solution.status == "ok",
        Solution.content_sig.is_not(None),
        Solution.content_sig == Task.content_sig,
    )
    ever_ok = exists().where(mine, Solution.status == "ok")
    return attempts, last_try, last_status, current_ok, ever_ok


def mark_for(row: dict) -> str:
    if row["current_ok"]:
        return "ok"
    if row["ever_ok"]:
        return "stale"
    if row["attempts"]:
        return "fail"
    return "none"


async def tasks_with_status(set_id: int, user_id: int) -> list[dict]:
    attempts, last_try, _, current_ok, ever_ok = task_status_columns(user_id)
    async with get_session() as session:
        rows = await session.execute(
            select(
                Task,
                attempts.label("attempts"),
                last_try.label("last_try"),
                current_ok.label("current_ok"),
                ever_ok.label("ever_ok"),
            )
            .where(Task.set_id == set_id)
            .order_by(func.coalesce(Task.pos, Task.id), Task.id)
        )
        out = []
        for task, n, last, ok_now, ok_ever in rows:
            item = as_dict(task)
            item.update(attempts=n, last_try=last, current_ok=ok_now, ever_ok=ok_ever)
            item["mark"] = mark_for(item)
            out.append(item)
        return out


async def personal_counts(user_id: int) -> tuple[int, int]:
    async with get_session() as session:
        total = (
            await session.execute(
                select(func.count())
                .select_from(Task)
                .join(PersonalSetAccess, PersonalSetAccess.set_id == Task.set_id)
                .where(PersonalSetAccess.user_id == user_id)
            )
        ).scalar_one()
        solved = (
            await session.execute(
                select(func.count(func.distinct(Task.id)))
                .select_from(Task)
                .join(PersonalSetAccess, PersonalSetAccess.set_id == Task.set_id)
                .join(Solution, Solution.task_id == Task.id)
                .where(
                    PersonalSetAccess.user_id == user_id,
                    Solution.user_id == user_id,
                    Solution.status == "ok",
                    Solution.content_sig.is_not(None),
                    Solution.content_sig == Task.content_sig,
                )
            )
        ).scalar_one()
        return solved, total


async def user_can_open(user_id: int, task: dict | None) -> bool:
    if not task:
        return False
    # обычная задача курса — её видят все
    if not task.get("set_id"):
        return True
    return await user_can_see_set(user_id, task["set_id"])


def _tests_json(tests: list[dict]) -> str:
    return json.dumps(tests, ensure_ascii=False)


async def create_personal_task(
    set_id: int,
    title: str,
    description: str,
    tests: list[dict],
    difficulty: int,
) -> int:
    tests_json = _tests_json(tests)
    async with get_session() as session:
        personal = await session.get(PersonalSet, set_id)
        task = Task(
            title=title,
            topic=personal.title,
            difficulty=difficulty,
            description=description,
            tests=tests_json,
            content_sig=content_sig(title, description, tests_json),
            set_id=set_id,
        )
        session.add(task)
        await session.commit()
        return task.id


async def update_personal_task(
    set_id: int,
    task_id: int,
    title: str,
    description: str,
    tests: list[dict],
    difficulty: int,
) -> bool:
    tests_json = _tests_json(tests)
    async with get_session() as session:
        personal = await session.get(PersonalSet, set_id)
        result = await session.execute(
            update(Task)
            .where(Task.id == task_id, Task.set_id == set_id)
            .values(
                title=title,
                topic=personal.title,
                difficulty=difficulty,
                description=description,
                tests=tests_json,
                content_sig=content_sig(title, description, tests_json),
            )
        )
        await session.commit()
        return result.rowcount > 0


async def set_task_pos(task_id: int, pos: int):
    async with get_session() as session:
        await session.execute(update(Task).where(Task.id == task_id).values(pos=pos))
        await session.commit()


async def delete_personal_task(set_id: int, task_id: int) -> bool:
    async with get_session() as session:
        task = (
            await session.execute(select(Task.id).where(Task.id == task_id, Task.set_id == set_id))
        ).first()
        if not task:
            return False
        await session.execute(delete(Solution).where(Solution.task_id == task_id))
        await session.execute(delete(Task).where(Task.id == task_id, Task.set_id == set_id))
        await session.commit()
        return True
