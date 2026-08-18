from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config.states import MAIN_MENU


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["in_settings"] = False
    keyboard = [
        [InlineKeyboardButton("📚 Порешать задачи", callback_data="modul_db", style="success")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings", style="primary")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            text="Главное меню. Можно порешать задачи.",
            reply_markup=markup,
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Главное меню. Можно порешать задачи.",
            reply_markup=markup,
        )
    return MAIN_MENU
