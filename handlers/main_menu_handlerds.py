from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
)
from config.states import MAIN_MENU


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer() 
        keyboard = [
            [InlineKeyboardButton("Новая задача", callback_data="gpt_ask")],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Вы в главном меню.",  
        )
    return MAIN_MENU