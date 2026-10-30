from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy import update as sql_update

import handlers.gpt_handlers as gh
from db.database import get_session, on_startup
from db.models import Event, User
from db.offer_crud import users_due_for_offer
from db.users_crud import get_user
from db.zadacha_crud import add_solution, next_task_for
from handlers.offer import offer_parents, offer_tick, offer_trial
from handlers.start_handler import start_handler
from services.progress import level_for, progress_text
from tests.fakes import FakeBot, make_context, make_update


def test_levels():
    assert level_for(0) == (0, None, 1)
    assert level_for(1)[1] == "Запустил print"
    assert level_for(4)[0] == 2
    assert level_for(100)[2] is None
    assert "Новый уровень" in progress_text(2, 3)
    assert "Новый уровень" not in progress_text(3, 4)
    assert "До следующего — 1" in progress_text(3, 4)


@pytest.fixture
def no_docker_no_llm(monkeypatch):
    async def fake_run(code, tests):
        ok = code == "ok"
        return ok, [{"n": 1, "ok": ok, "input": "", "expected": "1", "actual": "0"}]

    async def fake_review(*args, **kwargs):
        return "<b>разнос</b>"

    monkeypatch.setattr(gh, "run_tests", fake_run)
    monkeypatch.setattr(gh, "review_solution", fake_review)


async def kinds(user_id):
    async with get_session() as session:
        return (await session.execute(select(Event.kind).where(Event.user_id == user_id))).scalars().all()


async def test_offer_comes_once_on_tenth_solve(no_docker_no_llm):
    await on_startup()
    bot = FakeBot()
    upd, _ = make_update(tg_id=6001, bot=bot)
    context = make_context(bot)
    await start_handler(upd, context)
    user = await get_user(6001)

    for i in range(12):
        task = await next_task_for(user["id"])
        context.user_data["task_id"] = task["id"]
        upd, _ = make_update(tg_id=6001, text="ok", bot=bot)
        await gh.check_solution(upd, context)

    texts = [m["text"] for m in bot.sent]
    offers = [t for t in texts if "Первый урок бесплатный" in t]
    assert len(offers) == 1
    assert any("Новый уровень: «Почти не стыдно»" in t for t in texts)
    assert (await kinds(user["id"])).count("offer_shown") == 1


async def test_students_never_get_offer(no_docker_no_llm):
    await on_startup()
    # Александр из weekend_sets — у него личные блоки
    alex = await get_user(8500017318)
    bot = FakeBot()
    context = make_context(bot)
    for _ in range(10):
        task = await next_task_for(alex["id"])
        context.user_data["task_id"] = task["id"]
        upd, _ = make_update(tg_id=8500017318, text="ok", bot=bot)
        await gh.check_solution(upd, context)
    assert not any("Первый урок бесплатный" in m["text"] for m in bot.sent)

    async with get_session() as session:
        await session.execute(
            sql_update(User)
            .where(User.id == alex["id"])
            .values(created_at=datetime.now(timezone.utc) - timedelta(days=10))
        )
        await session.commit()
    assert await offer_tick(FakeBot()) == 0


async def test_timer_offer_after_three_days_and_one_repeat():
    await on_startup()
    bot = FakeBot()
    upd, _ = make_update(tg_id=6002, bot=bot)
    await start_handler(upd, make_context(bot))
    user = await get_user(6002)

    async def solve(n):
        for _ in range(n):
            task = await next_task_for(user["id"])
            await add_solution(user["id"], task["id"], "ok", "ok", [])

    async def age(**kw):
        async with get_session() as session:
            await session.execute(sql_update(User).where(User.id == user["id"]).values(**kw))
            await session.commit()

    await solve(2)
    await age(created_at=datetime.now(timezone.utc) - timedelta(days=4))
    assert await offer_tick(FakeBot()) == 0  # решил мало

    await solve(1)
    tick_bot = FakeBot()
    assert await offer_tick(tick_bot) == 1
    assert tick_bot.sent[0]["chat_id"] == 6002
    assert await offer_tick(FakeBot()) == 0  # второй раз сразу не шлём

    await age(offer_sent_at=datetime.now(timezone.utc) - timedelta(days=8))
    assert await offer_tick(FakeBot()) == 1  # повтор через неделю
    await age(offer_sent_at=datetime.now(timezone.utc) - timedelta(days=8))
    assert await offer_tick(FakeBot()) == 0  # больше двух раз не надоедаем


async def test_trial_click_stops_offers_and_parents_text_has_count():
    await on_startup()
    bot = FakeBot()
    upd, _ = make_update(tg_id=6003, bot=bot)
    await start_handler(upd, make_context(bot))
    user = await get_user(6003)
    for _ in range(3):
        task = await next_task_for(user["id"])
        await add_solution(user["id"], task["id"], "ok", "ok", [])

    upd, bot = make_update(tg_id=6003, data="offer_trial")
    await offer_trial(upd, make_context(bot))
    assert "url" not in bot.sent[0] and "Записаться" in str(bot.sent[0]["reply_markup"])

    upd, bot = make_update(tg_id=6003, data="offer_parents")
    await offer_parents(upd, make_context(bot))
    assert "решил 3 задач" in bot.sent[-1]["text"]
    assert "reply_markup" not in bot.sent[-1]

    async with get_session() as session:
        await session.execute(
            sql_update(User)
            .where(User.id == user["id"])
            .values(created_at=datetime.now(timezone.utc) - timedelta(days=10))
        )
        await session.commit()
    due = await users_due_for_offer(after_days=3, min_solved=3, repeat_days=7, max_shows=2)
    assert user["id"] not in [d["id"] for d in due]
    assert {"trial_click", "parents_text"} <= set(await kinds(user["id"]))
