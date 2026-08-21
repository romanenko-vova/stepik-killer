from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config.states import MAIN_MENU
from db.users_crud import create_user, get_user
from db.zadacha_crud import get_progress


async def main_menu_text(tg_id: int) -> str:
    user = await get_user(tg_id)
    if not user:
        user = await create_user(tg_id)

    solved, total = await get_progress(user["id"])
    if total == 0:
        progress = "Задач пока нет — каталог пустой."
    elif solved == 0:
        progress = f"Прогресс: 0 из {total}. Пока ни одной."
    elif solved == total:
        progress = f"Прогресс: {solved} из {total}. Все закрыты."
    else:
        progress = f"Прогресс: {solved} из {total}."

    return (
        "Тут надо решать задачи на Python.\n\n"
        "Жми «Порешать задачи», выбирай модуль и тему, пиши код одним сообщением. "
        "Бот прогонит тесты и скажет, прошло или нет. "
        "Если застрял — внутри задачи есть подсказка.\n\n"
        f"{progress}"
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["in_settings"] = False
    keyboard = [
        [InlineKeyboardButton("📚 Порешать задачи", callback_data="modul_db", style="success")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings", style="primary")],
    ]
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
