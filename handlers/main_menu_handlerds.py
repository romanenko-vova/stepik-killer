from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config.states import MAIN_MENU
from db.personal_crud import personal_counts
from db.users_crud import create_user, get_user
from db.zadacha_crud import get_progress, starter_progress


async def main_menu_text(tg_id: int) -> str:
    user = await get_user(tg_id)
    if not user:
        user = await create_user(tg_id)

    solved, total, stale = await get_progress(user["id"])
    starter_solved, starter_total = await starter_progress(user["id"])
    if total == 0:
        progress = "Задач пока нет — каталог пустой."
    elif solved == 0:
        progress = f"Прогресс: 0 из {total}. Пока ни одной."
    elif solved == total:
        progress = f"Прогресс: {solved} из {total}. Все закрыты."
    else:
        progress = f"Прогресс: {solved} из {total}."
    if stale:
        progress += f" Ещё {stale} изменились — их надо решить снова."

    personal_solved, personal_total = await personal_counts(user["id"])
    if personal_total:
        progress += f"\nПерсональные: {personal_solved} из {personal_total}."

    if starter_total and starter_solved < starter_total:
        progress = f"Стартовый набор: {starter_solved} из {starter_total}.\n" + progress

    return (
        "«Следующая задача» — продолжить с того места, где остановился. "
        "«Все задачи» — выбрать модуль и тему самому.\n\n"
        "Код присылай одним сообщением. Застрял — внутри задачи есть подсказка.\n\n"
        f"{progress}"
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["in_settings"] = False
    keyboard = [
        [InlineKeyboardButton("➡️ Следующая задача", callback_data="next_task", style="success")],
        [InlineKeyboardButton("📚 Все задачи", callback_data="modul_db", style="primary")],
    ]
    user = await get_user(update.effective_user.id)
    personal_total = 0
    if user:
        _, personal_total = await personal_counts(user["id"])
    if personal_total:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "📌 Персональные задания",
                    callback_data="personal",
                    style="primary",
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings", style="primary")]
    )
    markup = InlineKeyboardMarkup(keyboard)
    text = await main_menu_text(update.effective_user.id)
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            text=text,
            reply_markup=markup,
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=markup,
        )
    return MAIN_MENU
