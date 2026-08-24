"""
Каталог курса «Питонификация» из db/catalog.json.
Кладётся сам при запуске бота. Вручную: python -m db.seed

Задачи обновляем на месте по ключу. Решения не трогаем.
Если текст или тесты изменились — старые ok остаются, но в боте горит 🔄.
"""

import asyncio
import hashlib
import json
from pathlib import Path

import aiosqlite

from config.config import DB_PATH
from db.module_crud import get_modules

CATALOG_PATH = Path(__file__).with_name("catalog.json")


def load_catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_sig() -> str:
    return hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()


def content_sig(title: str, description: str, tests_json: str, image: str | None = None) -> str:
    payload = json.dumps(
        {
            "title": title,
            "description": description,
            "tests": tests_json,
            "image": image or "",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def flatten_catalog(catalog: list) -> list[tuple]:
    # ключ по месту в курсе: модуль-тема-задача. порядок не меняем — id живёт
    items = []
    for mi, module in enumerate(catalog, 1):
        for ti, topic in enumerate(module["topics"], 1):
            for qi, task in enumerate(topic["tasks"], 1):
                key = f"{mi:02d}-{ti:02d}-{qi:02d}"
                items.append((key, module, topic, task))
    return items


async def saved_sig() -> str | None:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT sig FROM catalog_meta WHERE id = 1")
        row = await cur.fetchone()
        return row[0] if row else None


async def save_sig(sig: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO catalog_meta(id, sig) VALUES (1, ?)",
            (sig,),
        )
        await conn.commit()


async def _upsert_module(conn, title: str, description: str | None) -> int:
    cur = await conn.execute("SELECT id FROM modules WHERE title = ?", (title,))
    row = await cur.fetchone()
    if row:
        await conn.execute(
            "UPDATE modules SET description = ? WHERE id = ?",
            (description, row[0]),
        )
        return row[0]
    cur = await conn.execute(
        "INSERT INTO modules(title, description) VALUES(?, ?)",
        (title, description),
    )
    return cur.lastrowid


async def _upsert_topic(conn, title: str, module_id: int) -> int:
    cur = await conn.execute(
        "SELECT id FROM topics WHERE module_id = ? AND title = ?",
        (module_id, title),
    )
    row = await cur.fetchone()
    if row:
        return row[0]
    cur = await conn.execute(
        "INSERT INTO topics(title, module_id) VALUES(?, ?)",
        (title, module_id),
    )
    return cur.lastrowid


async def seed_if_empty():
    sig = catalog_sig()
    if await saved_sig() == sig and await get_modules():
        return

    catalog = load_catalog()
    items = flatten_catalog(catalog)

    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row

        for module in catalog:
            module_id = await _upsert_module(conn, module["title"], module.get("description"))
            for topic in module["topics"]:
                await _upsert_topic(conn, topic["title"], module_id)

        cur = await conn.execute("SELECT * FROM tasks")
        rows = [dict(r) for r in await cur.fetchall()]
        by_key = {r["cat_key"]: r for r in rows if r.get("cat_key")}

        # старая база без ключей — клеим по порядку id, решения не теряются
        if not by_key and rows:
            for row, (key, *_rest) in zip(rows, items):
                await conn.execute(
                    "UPDATE tasks SET cat_key = ? WHERE id = ?",
                    (key, row["id"]),
                )
                row["cat_key"] = key
                by_key[key] = row

        for key, _module, topic, task in items:
            tests_json = json.dumps(task["tests"], ensure_ascii=False)
            image = task.get("image")
            new_sig = content_sig(task["title"], task["description"], tests_json, image)
            existing = by_key.get(key)

            if existing:
                old_sig = existing.get("content_sig") or content_sig(
                    existing["title"],
                    existing["description"],
                    existing["tests"],
                    existing.get("image"),
                )
                # старым попыткам ставим подпись той версии, на которой их сдавали
                await conn.execute(
                    """UPDATE solutions
                       SET content_sig = ?
                       WHERE task_id = ? AND content_sig IS NULL""",
                    (old_sig, existing["id"]),
                )
                await conn.execute(
                    """UPDATE tasks
                       SET title = ?, topic = ?, difficulty = ?, description = ?,
                           tests = ?, image = ?, content_sig = ?, cat_key = ?
                       WHERE id = ?""",
                    (
                        task["title"],
                        topic["title"],
                        task["difficulty"],
                        task["description"],
                        tests_json,
                        image,
                        new_sig,
                        key,
                        existing["id"],
                    ),
                )
            else:
                await conn.execute(
                    """INSERT INTO tasks(
                           title, topic, difficulty, description, tests, image, cat_key, content_sig
                       ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        task["title"],
                        topic["title"],
                        task["difficulty"],
                        task["description"],
                        tests_json,
                        image,
                        key,
                        new_sig,
                    ),
                )

        await conn.commit()

    await save_sig(sig)


if __name__ == "__main__":
    from db.database import create_tables

    asyncio.run(create_tables(None))
