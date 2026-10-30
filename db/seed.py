"""
Каталог курса «Перекус» из db/catalog.json (собирается из course/, см. COURSE.md).
Кладётся сам при запуске бота. Вручную: python -m db.seed

Задачи обновляем на месте по ключу «модуль-тема-задача». Решения не трогаем.
Если текст или тесты изменились — старые ok остаются, но в боте горит 🔄.
Задачи, темы и модули, которых в каталоге больше нет, удаляются: иначе они висят
в меню пустыми и раздувают «решено N из M». Решения по удалённым задачам уходят вместе с ними.
"""

import asyncio
import hashlib
import json
from pathlib import Path

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert

from db.database import get_session
from db.models import CatalogMeta, Module, Solution, Task, Topic

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
    """(ключ, модуль, тема, задача, место в теме).

    Ключ связывает задачу в каталоге с id в базе, а через id — с решениями.
    У задач он записан явно ("key"), поэтому их можно переставлять внутри темы.
    Без "key" — старое правило по месту: модуль-тема-задача.
    """
    items = []
    for mi, module in enumerate(catalog, 1):
        for ti, topic in enumerate(module["topics"], 1):
            for qi, task in enumerate(topic["tasks"], 1):
                key = task.get("key") or f"{mi:02d}-{ti:02d}-{qi:02d}"
                items.append((key, module, topic, task, qi))
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


async def _drop_missing(session, catalog: list, keys: set[str]):
    # всё, чего в каталоге больше нет. личные задачи (set_id) и задачи без ключа не трогаем
    await session.execute(
        delete(Task).where(Task.set_id.is_(None), Task.cat_key.is_not(None), Task.cat_key.not_in(keys))
    )
    topics_by_module = {module["title"]: {topic["title"] for topic in module["topics"]} for module in catalog}
    modules = (await session.execute(select(Module))).scalars().all()
    for module in modules:
        if module.title not in topics_by_module:
            await session.delete(module)  # темы уйдут каскадом
            continue
        await session.execute(
            delete(Topic).where(Topic.module_id == module.id, Topic.title.not_in(topics_by_module[module.title]))
        )


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
                select(Task).where(Task.set_id.is_(None))
            )
        ).scalars().all()
        by_key = {row.cat_key: row for row in rows if row.cat_key}

        for key, _module, topic, task, pos in items:
            await _upsert_task(session, by_key.get(key), key, topic["title"], task, pos=pos)

        await _drop_missing(session, catalog, {key for key, *_ in items})
        await session.commit()

    await save_sig(sig)


async def _upsert_task(session, existing, key: str, topic_title: str, task: dict, pos=None):
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
                pos=pos,
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
    existing.pos = pos


if __name__ == "__main__":
    asyncio.run(seed_if_empty())
