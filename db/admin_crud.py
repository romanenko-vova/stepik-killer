from sqlalchemy import and_, func, select
from sqlalchemy.orm import aliased

from db.database import get_session
from db.models import Solution, Task, User
from db.personal_crud import mark_for, task_status_columns


def person_name(user: dict) -> str:
    if user.get("first_name"):
        return user["first_name"]
    if user.get("username"):
        return "@" + user["username"]
    return f"id {user['id_tg']}"


async def list_students() -> list[dict]:
    s = aliased(Solution)
    t = aliased(Task)
    s2 = aliased(Solution)
    t2 = aliased(Task)

    current = and_(
        s.status == "ok",
        s.content_sig.is_not(None),
        s.content_sig == t.content_sig,
    )
    solved = (
        select(func.count(func.distinct(s.task_id)))
        .select_from(s)
        .join(t, t.id == s.task_id)
        .where(s.user_id == User.id, t.set_id.is_(None), current)
        .scalar_subquery()
    )
    # решал старую версию и не перерешал новую
    solved_now = (
        select(s2.task_id)
        .join(t2, t2.id == s2.task_id)
        .where(
            s2.user_id == User.id,
            t2.set_id.is_(None),
            s2.status == "ok",
            s2.content_sig.is_not(None),
            s2.content_sig == t2.content_sig,
        )
    )
    stale = (
        select(func.count(func.distinct(s.task_id)))
        .select_from(s)
        .join(t, t.id == s.task_id)
        .where(
            s.user_id == User.id,
            t.set_id.is_(None),
            s.status == "ok",
            (s.content_sig.is_(None)) | (s.content_sig != t.content_sig),
            s.task_id.not_in(solved_now),
        )
        .scalar_subquery()
    )
    attempts = select(func.count()).select_from(s).where(s.user_id == User.id).scalar_subquery()
    last_try = select(func.max(s.created_at)).where(s.user_id == User.id).scalar_subquery()

    async with get_session() as session:
        total = (
            await session.execute(select(func.count()).select_from(Task).where(Task.set_id.is_(None)))
        ).scalar_one()
        rows = await session.execute(
            select(
                User.id,
                User.id_tg,
                User.username,
                User.first_name,
                User.created_at,
                solved.label("solved"),
                stale.label("stale"),
                attempts.label("attempts"),
                last_try.label("last_try"),
            ).order_by(last_try.is_(None), last_try.desc())
        )
        out = []
        for row in rows:
            item = dict(row._mapping)
            item["total"] = total
            item["name"] = person_name(item)
            out.append(item)
        return out


async def student_tasks(user_pk: int) -> list[dict]:
    attempts, last_try, last_status, current_ok, ever_ok = task_status_columns(user_pk)
    async with get_session() as session:
        rows = await session.execute(
            select(
                Task.id,
                Task.title,
                Task.topic,
                Task.content_sig,
                last_status.label("last_status"),
                last_try.label("last_try"),
                attempts.label("attempts"),
                current_ok.label("current_ok"),
                ever_ok.label("ever_ok"),
            )
            .where(Task.set_id.is_(None))
            .order_by(Task.id)
        )
        out = []
        for row in rows:
            item = dict(row._mapping)
            item["mark"] = mark_for(item)
            out.append(item)
        return out


async def student_solutions(user_pk: int, task_id: int) -> list[dict]:
    async with get_session() as session:
        rows = await session.execute(
            select(
                Solution.id,
                Solution.code,
                Solution.status,
                Solution.content_sig,
                Solution.created_at,
                Solution.tests_json,
                Solution.review,
                Task.content_sig.label("task_sig"),
            )
            .join(Task, Task.id == Solution.task_id)
            .where(Solution.user_id == user_pk, Solution.task_id == task_id)
            .order_by(Solution.id.desc())
        )
        return [dict(row._mapping) for row in rows]
