from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config.states import SETTINGS, TOXIC_LEVEL_CHOICE
from db.users_crud import create_user, get_user, set_toxic_level
from handlers.main_menu_handlerds import main_menu

TOXIC_LEVELS = {
    "low_toxic": 1,
    "medium_toxic": 2,
    "high_toxic": 3,
}

TOXIC_NAMES = {
    1: "Понимающий репетитор",
    2: "Старший брат",
    3: "Senior программист",
}

TOXIC_BUTTONS = (
    ("low_toxic", "Понимающий репетитор", "success"),
    ("medium_toxic", "Старший брат", "primary"),
    ("high_toxic", "Senior программист", "danger"),
)


def toxic_keyboard(current_level: int = 0, with_back: bool = False):
    keyboard = []
    for callback, title, style in TOXIC_BUTTONS:
        if TOXIC_LEVELS[callback] == current_level:
            title = f"✅ {title}"
        keyboard.append(
            [InlineKeyboardButton(title, callback_data=callback, style=style)]
        )
    if with_back:
        keyboard.append(
            [InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]
        )
    return InlineKeyboardMarkup(keyboard)


START_INTRO = (
    "Привет. Это учебник Python в Telegram.\n\n"
    "Ты решаешь задачи: переменные, условия, циклы, коллекции, функции. "
    "Станция называется «Романенко Учит» — это просто сеттинг вокруг обычных задач.\n\n"
    "Берёшь задачу, пишешь код одним сообщением. Бот прогоняет тесты. "
    "Если не сошлось — можно взять подсказку. Готовое решение сам не покажет."
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        user = await create_user(user_id)

    # ещё не выбрал тон — сначала кто мы, потом выбор
    if user["toxic_level"] == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=START_INTRO,
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Как со мной разговаривать?",
            reply_markup=toxic_keyboard(),
        )
        return TOXIC_LEVEL_CHOICE

    return await main_menu(update, context)


async def open_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["in_settings"] = True
    user = await get_user(update.effective_user.id)
    current = user["toxic_level"] if user else 0
    current_name = TOXIC_NAMES.get(current, "не выбран")
    text = f"Настройки\n\nСейчас тон: {current_name}"
    markup = toxic_keyboard(current, with_back=True)

    if query:
        await query.edit_message_text(text=text, reply_markup=markup)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=markup,
        )
    return SETTINGS


async def choose_toxic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    level = TOXIC_LEVELS[query.data]
    await set_toxic_level(update.effective_user.id, level)

    # из настроек остаёмся там же, чтобы было видно новый тон
    if context.user_data.get("in_settings"):
        return await open_settings(update, context)
    return await main_menu(update, context)
