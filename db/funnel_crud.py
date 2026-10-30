"""Воронка: старт → решил 1 / 5 / 10 → увидел оффер → нажал пробный / взял текст родителям."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import Date, case, cast, exists, func, select

from db.database import get_session
from db.models import Event, Solution, User
from db.offer_crud import is_student, solved_count_column


MSK = ZoneInfo("Europe/Moscow")


def _did(kind: str):
    return exists().where(Event.user_id == User.id, Event.kind == kind)


async def funnel_by_source(days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    solved = solved_count_column()
    source = func.coalesce(User.source, "—").label("source")
    query = (
        select(
            source,
            func.count().label("starts"),
            func.sum(case((solved >= 1, 1), else_=0)).label("solved_1"),
            func.sum(case((solved >= 5, 1), else_=0)).label("solved_5"),
            func.sum(case((solved >= 10, 1), else_=0)).label("solved_10"),
            func.sum(case((_did("offer_shown"), 1), else_=0)).label("offer_shown"),
            func.sum(case((_did("trial_click"), 1), else_=0)).label("trial_click"),
            func.sum(case((_did("parents_text"), 1), else_=0)).label("parents_text"),
        )
        .where(User.created_at >= since, ~is_student())
        .group_by(source)
        .order_by(func.count().desc())
    )
    async with get_session() as session:
        return [dict(r._mapping) for r in await session.execute(query)]


async def funnel_by_day(days: int = 14) -> list[dict]:
    # и граница периода, и группировка — по Москве, иначе вечером «сегодня» уезжает в завтра
    since = (datetime.now(MSK) - timedelta(days=days - 1)).date()
    day_users = cast(func.timezone(MSK.key, User.created_at), Date)
    day_events = cast(func.timezone(MSK.key, Event.created_at), Date)
    day_solutions = cast(func.timezone(MSK.key, Solution.created_at), Date)

    async with get_session() as session:
        starts = dict(
            (await session.execute(
                select(day_users, func.count()).where(day_users >= since).group_by(day_users)
            )).all()
        )
        active = dict(
            (await session.execute(
                select(day_solutions, func.count(func.distinct(Solution.user_id)))
                .where(day_solutions >= since)
                .group_by(day_solutions)
            )).all()
        )
        attempts = dict(
            (await session.execute(
                select(day_solutions, func.count()).where(day_solutions >= since).group_by(day_solutions)
            )).all()
        )
        by_kind = {}
        for kind in ("solved", "offer_shown", "trial_click", "parents_text"):
            by_kind[kind] = dict(
                (await session.execute(
                    select(day_events, func.count())
                    .where(day_events >= since, Event.kind == kind)
                    .group_by(day_events)
                )).all()
            )

    rows = []
    for i in range(days):
        day = since + timedelta(days=i)
        rows.append(
            {
                "day": day,
                "starts": starts.get(day, 0),
                "active": active.get(day, 0),
                "attempts": attempts.get(day, 0),
                "solved": by_kind["solved"].get(day, 0),
                "offer_shown": by_kind["offer_shown"].get(day, 0),
                "trial_click": by_kind["trial_click"].get(day, 0),
                "parents_text": by_kind["parents_text"].get(day, 0),
            }
        )
    return list(reversed(rows))
