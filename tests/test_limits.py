import asyncio

import handlers.gpt_handlers as gh
from db.database import on_startup
from db.users_crud import get_user
from db.zadacha_crud import add_solution, next_task_for
from handlers.start_handler import start_handler
from services.events import track
from tests.fakes import FakeBot, make_context, make_update


async def _new_user(tg_id):
    await on_startup()
    bot = FakeBot()
    upd, _ = make_update(tg_id=tg_id, bot=bot)
    context = make_context(bot)
    await start_handler(upd, context)
    return await get_user(tg_id), context, bot


async def test_daily_attempts_limit(monkeypatch):
    monkeypatch.setattr(gh, "ATTEMPTS_PER_DAY", 3)
    user, context, bot = await _new_user(7001)
    task = await next_task_for(user["id"])
    for _ in range(3):
        await add_solution(user["id"], task["id"], "x", "fail", [])

    called = []
    monkeypatch.setattr(gh, "run_tests", lambda *a: called.append(1))
    upd, _ = make_update(tg_id=7001, text="print(1)", bot=bot)
    await gh.check_solution(upd, context)
    assert not called
    assert "На сегодня всё" in bot.sent[-1]["text"]


async def test_hint_limit(monkeypatch):
    monkeypatch.setattr(gh, "HINTS_PER_DAY", 1)
    user, context, bot = await _new_user(7002)
    context.user_data["last_code"] = "x"
    await track(user["id"], "hint", {})
    upd, _ = make_update(tg_id=7002, data="hint", bot=bot)
    await gh.send_hint(upd, context)
    assert "Подсказок на сегодня больше нет" in bot.sent[-1]["text"]


async def test_second_submit_while_checking_is_rejected(monkeypatch):
    user, context, bot = await _new_user(7003)
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_run(code, tests):
        started.set()
        await release.wait()
        return False, [{"n": 1, "ok": False, "input": "", "expected": "1", "actual": "0"}]

    async def fake_review(*a, **k):
        return "разнос"

    monkeypatch.setattr(gh, "run_tests", slow_run)
    monkeypatch.setattr(gh, "review_solution", fake_review)

    upd1, _ = make_update(tg_id=7003, text="a", bot=bot)
    first = asyncio.create_task(gh.check_solution(upd1, context))
    await started.wait()
    upd2, _ = make_update(tg_id=7003, text="b", bot=bot)
    await gh.check_solution(upd2, context)
    assert "ещё проверяю прошлый код" in bot.sent[-1]["text"]
    release.set()
    await first


async def test_hint_survives_llm_failure(monkeypatch):
    user, context, bot = await _new_user(7004)
    context.user_data["last_code"] = "x"

    async def broken(*a, **k):
        raise TimeoutError("openrouter спит")

    monkeypatch.setattr(gh, "give_hint", broken)
    upd, _ = make_update(tg_id=7004, data="hint", bot=bot)
    await gh.send_hint(upd, context)
    assert "не отвечает" in bot.sent[-1]["text"]
