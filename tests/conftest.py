"""
Тесты ходят в отдельную базу <POSTGRES_DB>_test на том же Postgres, что и разработка.
Рабочую базу не трогаем: тестовую пересоздаём и накатываем alembic на каждый запуск.
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _test_url(source: str) -> str:
    parts = urlsplit(source)
    name = parts.path.lstrip("/")
    if not name.endswith("_test"):
        name += "_test"
    return urlunsplit(parts._replace(path=f"/{name}"))


SOURCE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://stepik:stepik@127.0.0.1:5434/stepik_killer")
TEST_DATABASE_URL = _test_url(SOURCE_URL)
# подменяем до импорта приложения: engine создаётся при импорте db.database
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import psycopg  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _recreate_database():
    parts = urlsplit(TEST_DATABASE_URL.replace("+asyncpg", ""))
    name = parts.path.lstrip("/")
    admin = urlunsplit(parts._replace(path="/postgres"))
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{name}"')
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session", autouse=True)
def test_database():
    try:
        _recreate_database()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres недоступен: {exc}. Подними: docker compose up -d db")


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(test_database):
    import db.models  # noqa: F401
    from db.database import engine
    from db.models_base import Base

    yield
    names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
