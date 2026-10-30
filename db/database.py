from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.config import DATABASE_ECHO, DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=DATABASE_ECHO,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


def as_dict(obj) -> dict | None:
    # хендлеры и админка исторически работают со словарями из sqlite — не ломаем им жизнь
    if obj is None:
        return None
    return {attr.key: getattr(obj, attr.key) for attr in inspect(obj).mapper.column_attrs}


async def on_startup():
    # схему создаёт alembic (`alembic upgrade head`), тут только наполнение
    from db.seed import seed_if_empty
    from db.weekend_sets import ensure_weekend_sets

    await seed_if_empty()
    await ensure_weekend_sets()
