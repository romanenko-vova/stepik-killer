"""
Миграции гоняем синхронным драйвером psycopg — бот при этом остаётся на asyncpg.
URL берётся из DATABASE_URL (.env), postgresql+asyncpg:// меняем на postgresql+psycopg://.
"""

import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from alembic import context

load_dotenv()

# модели — только чтобы autogenerate видел таблицы. engine приложения не создаём
import db.models  # noqa: E402,F401
from db.models_base import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def sync_url() -> str:
    url = config.get_main_option("sqlalchemy.url") or os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL не задан")
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def run_migrations_offline() -> None:
    context.configure(
        url=sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(sync_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
