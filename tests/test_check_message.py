import handlers.gpt_handlers as gh
from db.database import on_startup
from db.users_crud import get_user
from db.zadacha_crud import next_task_for
from handlers.gpt_handlers import format_tests_html
from handlers.start_handler import start_handler
from tests.fakes import FakeBot, make_context, make_update


def test_only_task_visible_passes_are_shown():
    results = [{"n": i, "ok": True} for i in range(1, 6)] + [
        {"n": 6, "ok": False, "input": "6", "expected": "36", "actual": "12"}
    ]
    text = format_tests_html(results)
    assert "Тест 1:</b> ✅" in text and "Тест 3:</b> ✅" in text
    assert "Тест 4" not in text and "Тест 5" not in text
    assert "Тест 6:</b> ❌" in text and "36" in text


async def test_roast_appended_below_tests_with_buttons(monkeypatch):
    import asyncio

    async def fake_run(code, tests):
        return False, [{"n": 1, "ok": True}, {"n": 2, "ok": False, "input": "2", "expected": "4", "actual": "22"}]

    async def fake_review(*a, **k):
        return "<b>Панч про склейку строк</b>\n\nразнос"

    monkeypatch.setattr(gh, "run_tests", fake_run)
    monkeypatch.setattr(gh, "review_solution", fake_review)

    await on_startup()
    bot = FakeBot()
    upd, _ = make_update(tg_id=8101, bot=bot)
    context = make_context(bot)
    await start_handler(upd, context)
    user = await get_user(8101)
    context.user_data["task_id"] = (await next_task_for(user["id"]))["id"]

    upd, _ = make_update(tg_id=8101, text="print(input()+input())", bot=bot)
    await gh.check_solution(upd, context)
    for _ in range(50):
        if any("Панч" in m["text"] for m in bot.sent):
            break
        await asyncio.sleep(0.05)

    final = next(m for m in bot.sent if "Панч" in m["text"])
    assert final.get("edit")  # то же сообщение, не новое
    text = final["text"]
    assert text.index("Не принято") < text.index("Тест 2") < text.index("Панч")
    assert "Дай подсказку" in str(final["reply_markup"])
