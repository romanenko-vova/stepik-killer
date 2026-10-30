from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, exists, func, or_, select, update

from db.database import get_session
from db.models import PersonalSetAccess, Solution, Task, User


def solved_count_column():
    # сколько задач решено на текущих версиях — подзапросом по пользователю
    return (
        select(func.count(func.distinct(Solution.task_id)))
        .join(Task, Task.id == Solution.task_id)
        .where(
            Solution.user_id == User.id,
            Solution.status == "ok",
            Solution.content_sig.is_not(None),
            Solution.content_sig == Task.content_sig,
        )
        .scalar_subquery()
    )


def is_student():
    # у кого есть личный блок — уже занимается, ему оффер не нужен
    return exists().where(PersonalSetAccess.user_id == User.id)


async def users_due_for_offer(
    *,
    now: datetime | None = None,
    after_days: int,
    min_solved: int,
    repeat_days: int,
    max_shows: int,
) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    solved = solved_count_column()
    first = and_(
        User.offer_count == 0,
        User.created_at <= now - timedelta(days=after_days),
        solved >= min_solved,
    )
    repeat = and_(
        User.offer_count >= 1,
        User.offer_count < max_shows,
        User.offer_sent_at <= now - timedelta(days=repeat_days),
    )
    async with get_session() as session:
        rows = await session.execute(
            select(User.id, User.id_tg, User.offer_count, solved.label("solved"))
            .where(User.trial_clicked_at.is_(None), ~is_student(), or_(first, repeat))
            .order_by(User.id)
            .limit(200)
        )
        return [dict(r._mapping) for r in rows]


async def claim_offer(user_id: int, expected_count: int) -> bool:
    """Помечаем показ ДО отправки. Если кто-то успел раньше — счётчик уже другой, второй раз не шлём."""
    async with get_session() as session:
        result = await session.execute(
            update(User)
            .where(User.id == user_id, User.offer_count == expected_count)
            .values(offer_count=User.offer_count + 1, offer_sent_at=func.now())
        )
        await session.commit()
        return result.rowcount == 1


async def offer_state(user_id: int) -> dict:
    async with get_session() as session:
        row = await session.execute(
            select(User.offer_count, User.trial_clicked_at, is_student().label("student")).where(
                User.id == user_id
            )
        )
        return dict(row.one()._mapping)


async def mark_trial_click(user_id: int):
    async with get_session() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id, User.trial_clicked_at.is_(None))
            .values(trial_clicked_at=func.now())
        )
        await session.commit()
