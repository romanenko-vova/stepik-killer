import json
import sqlite3

from db.database import on_startup
from db.users_crud import create_user, get_user
from db.zadacha_crud import add_solution, get_progress
from scripts.migrate_sqlite_to_pg import migrate

# схема SQLite как в проде до переезда (db/database.py, коммит 6b5c5e3)
SQLITE_SCHEMA = """
CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, id_tg INTEGER UNIQUE, username TEXT NULL,
    first_name TEXT NULL, toxic_level INTEGER DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE modules(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE topics(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NULL,
    module_id INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, topic TEXT NOT NULL,
    difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 3), description TEXT NOT NULL,
    tests TEXT NOT NULL, image TEXT, cat_key TEXT, content_sig TEXT, set_id INTEGER, pos INTEGER);
CREATE TABLE personal_sets(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE personal_set_access(set_id INTEGER NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY (set_id, user_id));
CREATE TABLE catalog_meta(id INTEGER PRIMARY KEY CHECK (id = 1), sig TEXT NOT NULL);
CREATE TABLE solutions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, task_id INTEGER NOT NULL,
    code TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new', content_sig TEXT, tests_json TEXT, review TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""


def make_sqlite(path):
    conn = sqlite3.connect(path)
    conn.executescript(SQLITE_SCHEMA)
    conn.execute("INSERT INTO users(id, id_tg, username, first_name, toxic_level, created_at) VALUES (5, 8500017318, 'sasha', 'Саша', 3, '2026-10-17 09:00:00')")
    conn.execute("INSERT INTO users(id, id_tg, toxic_level) VALUES (9, 431425615, NULL)")
    conn.execute("INSERT INTO modules(id, title) VALUES (1, 'М')")
    conn.execute("INSERT INTO topics(id, title, module_id) VALUES (1, 'Т', 1)")
    conn.execute("INSERT INTO personal_sets(id, user_id, title) VALUES (3, 5, 'Блок')")
    conn.execute("INSERT INTO personal_set_access VALUES (3, 5), (3, 9)")
    tests = json.dumps([{"input": "1", "expected": "1"}], ensure_ascii=False)
    conn.execute("INSERT INTO tasks(id, title, topic, difficulty, description, tests, cat_key, content_sig) VALUES (40, 'Курс', 'Т', 1, 'у', ?, '01-01-01', 'sig40')", (tests,))
    conn.execute("INSERT INTO tasks(id, title, topic, difficulty, description, tests, content_sig, set_id, pos) VALUES (41, 'Личная', 'Блок', 2, 'у', ?, 'sig41', 3, 0)", (tests,))
    conn.execute("INSERT INTO catalog_meta VALUES (1, 'abc')")
    conn.execute("INSERT INTO solutions(id, user_id, task_id, code, status, content_sig, review, created_at) VALUES (100, 5, 40, 'print(1)', 'ok', 'sig40', '<b>ок</b>', '2026-10-17 10:00:00')")
    conn.execute("INSERT INTO solutions(id, user_id, task_id, code, status) VALUES (101, 5, 41, 'x', 'fail')")
    # задачу удалили, решение осталось: SQLite внешние ключи не проверял
    conn.execute("INSERT INTO solutions(id, user_id, task_id, code, status) VALUES (102, 5, 999, 'y', 'fail')")
    conn.commit()
    conn.close()


async def test_migration_is_complete_and_idempotent(tmp_path):
    db = tmp_path / "prod.db"
    make_sqlite(db)
    report = tmp_path / "report.md"

    assert await migrate(db, report)
    assert await migrate(db, report)  # второй прогон ничего не ломает и не дублирует

    text = report.read_text(encoding="utf-8")
    assert "всё сошлось" in text
    assert "| solutions | 3 | 2 | 1 | 2 |" in text

    orphans = json.loads(report.with_suffix(".orphans.json").read_text(encoding="utf-8"))
    assert orphans["solutions"][0]["row"]["id"] == 102

    sasha = await get_user(8500017318)
    assert sasha["id"] == 5
    assert sasha["toxic_level"] == 3
    assert sasha["created_at"].isoformat().startswith("2026-10-17T09:00:00")
    assert (await get_user(431425615))["toxic_level"] == 0

    solved, _, _ = await get_progress(5)
    assert solved == 1

    # счётчики id сдвинуты: новые записи не налетают на перенесённые
    new_user = await create_user(1)
    assert new_user["id"] == 10
    assert await add_solution(5, 40, "z", "fail", []) == 103


async def test_bot_starts_on_migrated_database(tmp_path):
    db = tmp_path / "prod.db"
    make_sqlite(db)
    assert await migrate(db, tmp_path / "r.md")
    # сидинг каталога и личные блоки должны встать поверх перенесённых данных без ошибок
    await on_startup()
    await on_startup()
