"""
Каталог курса «Питонификация» из db/catalog.json.
Кладётся сам при запуске бота. Вручную: python -m db.seed
"""

import asyncio
import hashlib
import json
from pathlib import Path

import aiosqlite

from config.config import DB_PATH
from db.module_crud import add_module, get_modules
from db.topic_crud import add_topic
from db.zadacha_crud import add_task

CATALOG_PATH = Path(__file__).with_name("catalog.json")


def load_catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_sig() -> str:
    # если json поменяли — при старте пересоберём каталог
    return hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()


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


async def clear_catalog():
    # юзеров не трогаем, каталог пересобираем
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM solutions")
        await conn.execute("DELETE FROM tasks")
        await conn.execute("DELETE FROM topics")
        await conn.execute("DELETE FROM modules")
        await conn.commit()


async def seed_if_empty():
    sig = catalog_sig()
    if await saved_sig() == sig and await get_modules():
        return

    await clear_catalog()
    catalog = load_catalog()

    for module in catalog:
        module_id = await add_module(module["title"], module["description"])
        for topic in module["topics"]:
            await add_topic(topic["title"], module_id)
            for task in topic["tasks"]:
                await add_task(
                    task["title"],
                    topic["title"],
                    task["difficulty"],
                    task["description"],
                    json.dumps(task["tests"], ensure_ascii=False),
                    task.get("image"),
                )

    await save_sig(sig)


if __name__ == "__main__":
    from db.database import create_tables

    asyncio.run(create_tables(None))
