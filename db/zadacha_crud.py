import json

from sqlalchemy import and_, func, or_, select, update

from db.database import as_dict, get_session
from db.models import Solution, Task


async def add_task(
    title: str,
    topic: str,
    difficulty: int,
    description: str,
    tests_json: str,
    image: str | None = None,
):
    async with get_session() as session:
        task = Task(
            title=title,
            topic=topic,
            difficulty=difficulty,
            description=description,
            tests=tests_json,
            image=image,
        )
        session.add(task)
        await session.commit()
        return task.id


async def get_task(task_id: int):
    async with get_session() as session:
        return as_dict(await session.get(Task, task_id))


async def get_tasks_by_topic(topic_title: str):
    # set_id — личные задачи, в общую тему их не мешаем
    async with get_session() as session:
        rows = (
            await session.execute(
                select(Task).where(Task.topic == topic_title, Task.set_id.is_(None)).order_by(Task.id)
            )
        ).scalars().all()
        return [as_dict(row) for row in rows]


def _current_ok():
    # решение засчитано на ТЕКУЩЕЙ версии условия
    return and_(
        Solution.status == "ok",
        Solution.content_sig.is_not(None),
        Solution.content_sig == Task.content_sig,
    )


async def get_solved_task_ids(user_id: int, catalog_only: bool = False) -> set[int]:
    query = (
        select(Solution.task_id)
        .join(Task, Task.id == Solution.task_id)
        .where(Solution.user_id == user_id, _current_ok())
        .distinct()
    )
    if catalog_only:
        query = query.where(Task.set_id.is_(None))
    async with get_session() as session:
        return set((await session.execute(query)).scalars().all())


async def get_stale_task_ids(user_id: int, catalog_only: bool = False) -> set[int]:
    # когда-то решил, но задача с тех пор поменялась
    solved = await get_solved_task_ids(user_id, catalog_only=catalog_only)
    query = (
        select(Solution.task_id)
        .join(Task, Task.id == Solution.task_id)
        .where(
            Solution.user_id == user_id,
            Solution.status == "ok",
            or_(Solution.content_sig.is_(None), Solution.content_sig != Task.content_sig),
        )
        .distinct()
    )
    if catalog_only:
        query = query.where(Task.set_id.is_(None))
    async with get_session() as session:
        return set((await session.execute(query)).scalars().all()) - solved


async def get_progress(user_id: int) -> tuple[int, int, int]:
    # личные задачи в общий прогресс курса не входят
    async with get_session() as session:
        total = (
            await session.execute(select(func.count()).select_from(Task).where(Task.set_id.is_(None)))
        ).scalar_one()
    solved = len(await get_solved_task_ids(user_id, catalog_only=True))
    stale = len(await get_stale_task_ids(user_id, catalog_only=True))
    return solved, total, stale


async def count_solved(user_id: int) -> int:
    # всё решённое на текущих версиях: и курс, и личные блоки
    return len(await get_solved_task_ids(user_id))


async def add_solution(
    user_id: int,
    task_id: int,
    code: str,
    status: str = "new",
    tests_report: list | None = None,
):
    tests_json = json.dumps(tests_report, ensure_ascii=False) if tests_report is not None else None
    async with get_session() as session:
        task = await session.get(Task, task_id)
        solution = Solution(
            user_id=user_id,
            task_id=task_id,
            code=code,
            status=status,
            content_sig=task.content_sig if task else None,
            tests_json=tests_json,
        )
        session.add(solution)
        await session.commit()
        return solution.id


async def set_solution_review(solution_id: int, review: str):
    async with get_session() as session:
        await session.execute(update(Solution).where(Solution.id == solution_id).values(review=review))
        await session.commit()


async def get_attempt_count(user_id: int, task_id: int) -> int:
    async with get_session() as session:
        return (
            await session.execute(
                select(func.count())
                .select_from(Solution)
                .where(Solution.user_id == user_id, Solution.task_id == task_id)
            )
        ).scalar_one()


async def get_recent_attempts(user_id: int, task_id: int, limit: int = 3):
    async with get_session() as session:
        rows = await session.execute(
            select(Solution.code, Solution.status, Solution.created_at, Solution.review)
            .where(Solution.user_id == user_id, Solution.task_id == task_id)
            .order_by(Solution.id.desc())
            .limit(limit)
        )
        return [dict(row._mapping) for row in reversed(rows.all())]


async def attempts_today(user_id: int) -> int:
    # для лимита попыток в сутки
    async with get_session() as session:
        return (
            await session.execute(
                select(func.count())
                .select_from(Solution)
                .where(
                    Solution.user_id == user_id,
                    Solution.created_at >= func.now() - func.make_interval(0, 0, 0, 1),
                )
            )
        ).scalar_one()
