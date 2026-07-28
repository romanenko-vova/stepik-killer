from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ContextTypes,
)

from config.states import MAIN_MENU


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Новая задача", callback_data="gpt_ask")],
        [InlineKeyboardButton("Решать модули", callback_data="modul_db")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            text="Вы в главном меню.",
            reply_markup=markup,
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Вы в главном меню.",
            reply_markup=markup,
        )
    return MAIN_MENU
