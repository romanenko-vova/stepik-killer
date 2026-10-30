import json

from sqlalchemy import select

from config.states import SOLVING
from db.database import get_session, on_startup
from db.models import Event
from db.seed import seed_starter
from db.users_crud import get_user
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


def test_task_text_shows_two_examples_and_hides_the_rest():
    task = {
        "title": "Т",
        "description": "У",
        "tests": json.dumps([{"input": str(i), "expected": str(i)} for i in range(6)]),
    }
    text = format_task_text(task)
    assert "Пример 2" in text
    assert "Пример 3" not in text
    assert "Ещё 4 скрытых теста" in text


async def test_starter_seed_is_idempotent_and_ordered():
    await seed_starter()
    await seed_starter()
    from db.models import Task

    async with get_session() as session:
        rows = (
            await session.execute(select(Task).where(Task.starter_pos.is_not(None)).order_by(Task.starter_pos))
        ).scalars().all()
    assert [t.starter_pos for t in rows] == list(range(1, 11))
    assert all(len(json.loads(t.tests)) >= 6 for t in rows)


async def test_new_user_gets_first_task_immediately():
    await on_startup()
    update, bot = make_update(tg_id=5001)
    context = make_context(bot, args=["reel_7"])

    state = await start_handler(update, context)

    assert state == SOLVING
    texts = [m["text"] for m in bot.sent]
    assert "NotToxicPythonbot" in texts[0]
    assert "Романенко" not in texts[0]
    assert "1. Позывной" in texts[1]
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


async def test_next_task_walks_starter_then_course():
    await on_startup()
    update, bot = make_update(tg_id=5003)
    await start_handler(update, make_context(bot))
    user = await get_user(5003)

    first = await next_task_for(user["id"])
    assert first["starter_pos"] == 1
    for _ in range(10):
        task = await next_task_for(user["id"])
        assert task["starter_pos"] is not None
        await add_solution(user["id"], task["id"], "ok", "ok", [])
    assert await starter_progress(user["id"]) == (10, 10)

    after = await next_task_for(user["id"])
    assert after["starter_pos"] is None
    assert after["cat_key"] == "01-01-01"
    await add_solution(user["id"], after["id"], "ok", "ok", [])
    # в первой теме осталось 5 задач, во второй первой идёт разминка, хотя её ключ 01-02-05
    for _ in range(5):
        task = await next_task_for(user["id"])
        await add_solution(user["id"], task["id"], "ok", "ok", [])
    assert (await next_task_for(user["id"]))["title"] == "Разгон. Последняя цифра"
