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

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from db.database import get_session
from db.models import CatalogMeta, Module, Solution, Task, Topic

CATALOG_PATH = Path(__file__).with_name("catalog.json")
STARTER_PATH = Path(__file__).with_name("starter.json")
STARTER_TOPIC = "Старт"


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
    async with get_session() as session:
        meta = await session.get(CatalogMeta, 1)
        return meta.sig if meta else None


async def save_sig(sig: str):
    async with get_session() as session:
        await session.execute(
            insert(CatalogMeta)
            .values(id=1, sig=sig)
            .on_conflict_do_update(index_elements=[CatalogMeta.id], set_={"sig": sig})
        )
        await session.commit()


async def _upsert_module(session, title: str, description: str | None) -> int:
    module = (await session.execute(select(Module).where(Module.title == title))).scalars().first()
    if module:
        module.description = description
        return module.id
    module = Module(title=title, description=description)
    session.add(module)
    await session.flush()
    return module.id


async def _upsert_topic(session, title: str, module_id: int) -> int:
    topic = (
        await session.execute(select(Topic).where(Topic.module_id == module_id, Topic.title == title))
    ).scalars().first()
    if topic:
        return topic.id
    topic = Topic(title=title, module_id=module_id)
    session.add(topic)
    await session.flush()
    return topic.id


async def seed_if_empty():
    sig = catalog_sig()
    async with get_session() as session:
        has_modules = (await session.execute(select(Module.id).limit(1))).first() is not None
    if await saved_sig() == sig and has_modules:
        return

    catalog = load_catalog()
    items = flatten_catalog(catalog)

    async with get_session() as session:
        for module in catalog:
            module_id = await _upsert_module(session, module["title"], module.get("description"))
            for topic in module["topics"]:
                await _upsert_topic(session, topic["title"], module_id)

        rows = (
            await session.execute(
                select(Task).where(Task.set_id.is_(None), Task.starter_pos.is_(None))
            )
        ).scalars().all()
        by_key = {row.cat_key: row for row in rows if row.cat_key}

        for key, _module, topic, task in items:
            await _upsert_task(session, by_key.get(key), key, topic["title"], task)

        await session.commit()

    await save_sig(sig)


async def _upsert_task(session, existing, key: str, topic_title: str, task: dict, starter_pos=None):
    tests_json = json.dumps(task["tests"], ensure_ascii=False)
    image = task.get("image")
    new_sig = content_sig(task["title"], task["description"], tests_json, image)

    if existing is None:
        session.add(
            Task(
                title=task["title"],
                topic=topic_title,
                difficulty=task["difficulty"],
                description=task["description"],
                tests=tests_json,
                image=image,
                cat_key=key,
                content_sig=new_sig,
                starter_pos=starter_pos,
            )
        )
        return

    old_sig = existing.content_sig or content_sig(
        existing.title, existing.description, existing.tests, existing.image
    )
    # старым попыткам ставим подпись той версии, на которой их сдавали
    await session.execute(
        update(Solution)
        .where(Solution.task_id == existing.id, Solution.content_sig.is_(None))
        .values(content_sig=old_sig)
    )
    existing.title = task["title"]
    existing.topic = topic_title
    existing.difficulty = task["difficulty"]
    existing.description = task["description"]
    existing.tests = tests_json
    existing.image = image
    existing.content_sig = new_sig
    existing.starter_pos = starter_pos


async def seed_starter():
    """Стартовый набор для новичков: 10 задач по нарастающей, ключи start-01..start-10.

    В меню модулей его нет — новичок идёт по нему кнопкой «Следующая задача».
    Файл маленький, обновляем на каждом старте.
    """
    tasks = json.loads(STARTER_PATH.read_text(encoding="utf-8"))
    async with get_session() as session:
        rows = (
            await session.execute(select(Task).where(Task.cat_key.like("start-%")))
        ).scalars().all()
        by_key = {row.cat_key: row for row in rows}
        for pos, task in enumerate(tasks, 1):
            key = f"start-{pos:02d}"
            await _upsert_task(session, by_key.get(key), key, STARTER_TOPIC, task, starter_pos=pos)
        await session.commit()


async def _main():
    await seed_if_empty()
    await seed_starter()


if __name__ == "__main__":
    asyncio.run(_main())
