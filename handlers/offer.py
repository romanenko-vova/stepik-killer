"""
Оффер пробного урока подростку и готовый текст для родителей.

Срабатывает:
- сразу, когда решено OFFER_AFTER_SOLVED задач;
- фоном раз в час: через OFFER_AFTER_DAYS дней после старта при OFFER_MIN_SOLVED решённых,
  и повтор через OFFER_REPEAT_DAYS, если не нажал. Всего не больше OFFER_MAX_SHOWS раз.
Ученикам с личными блоками не показываем — они уже занимаются.
"""

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Forbidden, TelegramError
from telegram.ext import Application, ContextTypes

from config.config import (
    OFFER_AFTER_DAYS,
    OFFER_ENABLED,
    OFFER_AFTER_SOLVED,
    OFFER_MAX_SHOWS,
    OFFER_MIN_SOLVED,
    OFFER_REPEAT_DAYS,
    TRIAL_URL,
)
from config.funnel_texts import (
    OFFER_PARENTS_BUTTON,
    OFFER_REPEAT_TEXT,
    OFFER_TEXT,
    OFFER_TRIAL_BUTTON,
    PARENTS_INTRO,
    PARENTS_TEXT,
    TRIAL_LINK_BUTTON,
    TRIAL_REPLY,
)
from db.offer_crud import claim_offer, mark_trial_click, offer_state, users_due_for_offer
from db.users_crud import get_user
from db.zadacha_crud import count_solved
from services.events import track

logger = logging.getLogger(__name__)

OFFER_LOOP_SECONDS = 3600


def offer_markup() -> InlineKeyboardMarkup:
    # обе кнопки callback, не url: иначе клик не узнать
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(OFFER_TRIAL_BUTTON, callback_data="offer_trial", style="success")],
            [InlineKeyboardButton(OFFER_PARENTS_BUTTON, callback_data="offer_parents", style="primary")],
        ]
    )


async def send_offer(bot, user_id: int, chat_id: int, shows_before: int, solved: int, reason: str) -> bool:
    if not await claim_offer(user_id, shows_before):
        return False
    text = (OFFER_TEXT if shows_before == 0 else OFFER_REPEAT_TEXT).format(solved=solved)
    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=offer_markup())
    except Forbidden:
        # заблокировал бота — показ уже засчитан, больше не стучимся
        await track(user_id, "offer_blocked", {"reason": reason})
        return False
    await track(user_id, "offer_shown", {"reason": reason, "show": shows_before + 1, "solved": solved})
    return True


async def maybe_offer_after_solve(bot, user: dict, chat_id: int, solved: int):
    if not OFFER_ENABLED or solved < OFFER_AFTER_SOLVED:
        return
    state = await offer_state(user["id"])
    if state["student"] or state["trial_clicked_at"] or state["offer_count"] > 0:
        return
    await send_offer(bot, user["id"], chat_id, 0, solved, "solved")


async def offer_trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await get_user(update.effective_user.id)
    if user:
        await mark_trial_click(user["id"])
        await track(user["id"], "trial_click", None)
    await query.message.reply_text(
        TRIAL_REPLY,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(TRIAL_LINK_BUTTON, url=TRIAL_URL)],
                [InlineKeyboardButton(OFFER_PARENTS_BUTTON, callback_data="offer_parents")],
            ]
        ),
    )


async def offer_parents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await get_user(update.effective_user.id)
    solved = await count_solved(user["id"]) if user else 0
    if user:
        await track(user["id"], "parents_text", {"solved": solved})
    await query.message.reply_text(PARENTS_INTRO)
    # отдельным сообщением без кнопок — чтобы переслать ровно его
    await query.message.reply_text(PARENTS_TEXT.format(solved=solved, url=TRIAL_URL))


async def offer_tick(bot):
    due = await users_due_for_offer(
        after_days=OFFER_AFTER_DAYS,
        min_solved=OFFER_MIN_SOLVED,
        repeat_days=OFFER_REPEAT_DAYS,
        max_shows=OFFER_MAX_SHOWS,
    )
    sent = 0
    for row in due:
        try:
            if await send_offer(bot, row["id"], row["id_tg"], row["offer_count"], row["solved"], "timer"):
                sent += 1
        except TelegramError:
            logger.exception("оффер не ушёл пользователю %s", row["id"])
        # Telegram не любит больше ~30 сообщений в секунду
        await asyncio.sleep(0.1)
    return sent


async def offer_loop(app: Application):
    if not OFFER_ENABLED:
        logger.info("оффер выключен (OFFER_ENABLED), фоновый цикл не запускаю")
        return
    while True:
        try:
            sent = await offer_tick(app.bot)
            if sent:
                logger.info("офферов отправлено: %s", sent)
        except Exception:
            logger.exception("цикл офферов упал, попробую через час")
        await asyncio.sleep(OFFER_LOOP_SECONDS)
