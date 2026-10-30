import json

from sqlalchemy import select

from config.states import SOLVING
from db.database import get_session, on_startup
from db.models import Event
from db.users_crud import get_user
import db.zadacha_crud as zc
from db.zadacha_crud import add_solution, next_task_for, starter_progress
from handlers.gpt_handlers import format_task_text
from handlers.start_handler import parse_source, start_handler
from tests.fakes import make_context, make_update


def test_parse_source_accepts_only_safe_values():
    assert parse_source(["reel_12"]) == "reel_12"
    assert parse_source(["tiktok-3"]) == "tiktok-3"
    assert parse_source([]) is None
    assert parse_source(["<script>"]) is None
    assert parse_source(["a" * 65]) is None


async def test_new_user_gets_first_task_immediately():
    await on_startup()
    update, bot = make_update(tg_id=5001)
    context = make_context(bot, args=["reel_7"])

    state = await start_handler(update, context)

    assert state == SOLVING
    texts = [m["text"] for m in bot.sent]
    assert "NotToxicPythonbot" in texts[0]
    assert "Романенко" not in texts[0]
    # стартовый набор не задан — первая задача каталога
    assert "Задание 1. Приветствие" in texts[1]
    assert context.user_data["task_id"]

    user = await get_user(5001)
    assert user["toxic_level"] == 3
    assert user["source"] == "reel_7"

    async with get_session() as session:
        kinds = (await session.execute(select(Event.kind).where(Event.user_id == user["id"]))).scalars().all()
    assert "start" in kinds and "task_open" in kinds


async def test_returning_user_keeps_first_source_and_gets_menu():
    await on_startup()
    update, bot = make_update(tg_id=5002)
    await start_handler(update, make_context(bot, args=["reel_1"]))
    update, bot = make_update(tg_id=5002)
    await start_handler(update, make_context(bot, args=["reel_2"]))
    assert (await get_user(5002))["source"] == "reel_1"
    assert "Следующая задача" in str(bot.sent[-1]["reply_markup"])


async def test_next_task_walks_starter_keys_then_course(monkeypatch):
    # порядок из конфига, неизвестный ключ пропускается
    monkeypatch.setattr(zc, "STARTER_KEYS", ["02-01-01", "нет-такого", "01-02-05"])
    await on_startup()
    upd, bot = make_update(tg_id=5003)
    await start_handler(upd, make_context(bot))
    user = await get_user(5003)
    assert "Задание 1. Счёт до n" in bot.sent[1]["text"]

    first = await next_task_for(user["id"])
    assert first["cat_key"] == "02-01-01"
    await add_solution(user["id"], first["id"], "ok", "ok", [])
    second = await next_task_for(user["id"])
    assert second["cat_key"] == "01-02-05"
    assert await starter_progress(user["id"]) == (1, 2)

    await add_solution(user["id"], second["id"], "ok", "ok", [])
    # набор пройден — дальше курс по порядку
    assert (await next_task_for(user["id"]))["cat_key"] == "01-01-01"


async def test_next_task_without_starter_follows_catalog_order():
    await on_startup()
    upd, bot = make_update(tg_id=5004)
    await start_handler(upd, make_context(bot))
    user = await get_user(5004)
    keys = []
    for _ in range(8):
        task = await next_task_for(user["id"])
        keys.append(task["cat_key"])
        await add_solution(user["id"], task["id"], "ok", "ok", [])
    assert keys == [f"01-01-0{i}" for i in range(1, 7)] + ["01-02-01", "01-02-02"]
    assert await starter_progress(user["id"]) == (0, 0)
