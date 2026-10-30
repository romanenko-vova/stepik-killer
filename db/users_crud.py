from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from db.database import as_dict, get_session
from db.models import User


async def get_user(user_id: int):
    # user_id здесь — id в телеграме, так исторически
    async with get_session() as session:
        user = (await session.execute(select(User).where(User.id_tg == user_id))).scalar_one_or_none()
        return as_dict(user)


async def list_users() -> list[dict]:
    async with get_session() as session:
        rows = await session.execute(
            select(User.id, User.id_tg, User.username, User.first_name).order_by(
                User.first_name.nulls_last(), User.username.nulls_last(), User.id
            )
        )
        return [dict(row._mapping) for row in rows]


async def get_user_by_id(pk: int):
    async with get_session() as session:
        return as_dict(await session.get(User, pk))


async def create_user(
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    toxic_level: int = 0,
    source: str | None = None,
):
    # два быстрых /start подряд не должны падать на уникальности
    async with get_session() as session:
        await session.execute(
            insert(User)
            .values(
                id_tg=user_id,
                username=username,
                first_name=first_name,
                toxic_level=toxic_level,
                source=source,
            )
            .on_conflict_do_nothing(index_elements=[User.id_tg])
        )
        await session.commit()
    return await get_user(user_id)


async def touch_user(user_id: int, username: str | None = None, first_name: str | None = None):
    async with get_session() as session:
        await session.execute(
            update(User).where(User.id_tg == user_id).values(username=username, first_name=first_name)
        )
        await session.commit()
    return await get_user(user_id)


async def set_toxic_level(user_id: int, level: int):
    async with get_session() as session:
        await session.execute(update(User).where(User.id_tg == user_id).values(toxic_level=level))
        await session.commit()
