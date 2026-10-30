import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config.states import SETTINGS
from db.users_crud import create_user, get_user, set_toxic_level, touch_user
from db.zadacha_crud import next_task_for
from handlers.main_menu_handlerds import main_menu

TOXIC_LEVELS = {
    "low_toxic": 1,
    "medium_toxic": 2,
    "high_toxic": 3,
}

TOXIC_NAMES = {
    1: "Понимающий репетитор",
    2: "Старший брат",
    3: "Без пощады",
}

TOXIC_BUTTONS = (
    ("high_toxic", "🔥 Без пощады", "danger"),
    ("medium_toxic", "😏 Старший брат", "primary"),
    ("low_toxic", "🙂 Понимающий репетитор", "success"),
)

# новичок из рилса пришёл за разносом — сразу его и даём
DEFAULT_TOXIC = 3

# только то, что Telegram пропускает в deep-link: латиница, цифры, _ и -
SOURCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

START_INTRO = (
    "Я NotToxicPythonbot. Ты пишешь код — я проверяю его на тестах и разношу за ошибки.\n\n"
    "Режим сейчас: 🔥 Без пощады. Если станет слишком больно — /settings.\n"
    "Код присылай одним сообщением. Застрял — жми «Дай подсказку».\n\n"
    "Поехали, первая задача 👇"
)


def parse_source(args: list[str] | None) -> str | None:
    if not args:
        return None
    raw = args[0].strip()
    return raw if SOURCE_RE.match(raw) else None


def toxic_keyboard(current_level: int = 0, with_back: bool = False):
    keyboard = []
    for callback, title, style in TOXIC_BUTTONS:
        if TOXIC_LEVELS[callback] == current_level:
            title = f"✅ {title}"
        keyboard.append([InlineKeyboardButton(title, callback_data=callback, style=style)])
    if with_back:
        keyboard.append([InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")])
    return InlineKeyboardMarkup(keyboard)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # импорт здесь: gpt_handlers тянет start_handler через main_menu
    from handlers.gpt_handlers import send_task
    from services.events import track

    tg = update.effective_user
    source = parse_source(context.args)
    user = await get_user(tg.id)

    if user:
        await touch_user(tg.id, tg.username, tg.first_name)
        await track(user["id"], "start", {"source": source, "returning": True})
        return await main_menu(update, context)

    user = await create_user(tg.id, tg.username, tg.first_name, DEFAULT_TOXIC, source)
    await track(user["id"], "start", {"source": source, "returning": False})
    await context.bot.send_message(chat_id=update.effective_chat.id, text=START_INTRO)

    task = await next_task_for(user["id"])
    if task is None:
        return await main_menu(update, context)
    return await send_task(context, update.effective_chat.id, user, task)


async def open_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user = await get_user(update.effective_user.id)
    current = user["toxic_level"] if user else 0
    current_name = TOXIC_NAMES.get(current, "не выбран")
    text = (
        f"Настройки\n\nСейчас тон: {current_name}\n\n"
        "🔥 Без пощады — разнос за каждую ошибку\n"
        "😏 Старший брат — подколы, но по-доброму\n"
        "🙂 Понимающий репетитор — спокойно и по делу"
    )
    markup = toxic_keyboard(current, with_back=True)

    if query:
        await query.edit_message_text(text=text, reply_markup=markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=markup)
    return SETTINGS


async def choose_toxic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.events import track

    query = update.callback_query
    level = TOXIC_LEVELS[query.data]
    await set_toxic_level(update.effective_user.id, level)
    user = await get_user(update.effective_user.id)
    if user:
        await track(user["id"], "tone_changed", {"level": level})
    return await open_settings(update, context)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await open_settings(update, context)
