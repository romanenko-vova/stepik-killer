import asyncio

from openai import AsyncOpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config.states import GPT, MAIN_MENU, MODULS
from db.zadacha_crud import add_task
from services.code_runner import run_fake_test


async def start_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(text="Придумываю для тебя новую задачу.")
    context.application.create_task(generate_and_send_answer(update, context))
    return GPT


async def generate_and_send_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = AsyncOpenAI()

    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=[
            {"role": "system", "content": "Ты — генератор задач по Python."},
            {
                "role": "user",
                "content": "Придумай простенькую задачку на питоне. В конце напиши 'Напиши мне решение этой задачи'.",
            },
        ],
    )

    answer_text = response.output_text

    query = update.callback_query
    await query.edit_message_text(text=answer_text)
    
    context.user_data["current_task"] = {
        "condition": answer_text,
    }
    
    sample_tests = '[{"input_text":"1 1", "output_text": "2"}, {"input_text":"2 2", "output_text": "4"}]'
    await add_task("Задача", "списки", 1, answer_text, sample_tests)


async def check_solution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_message.text:
        await update.message.reply_text("Пришлите текст кода для проверки.")
        return GPT

    user_code = update.effective_message.text
    context.user_data["user_code"] = user_code

    keyboard = [[InlineKeyboardButton("Проверить решение", callback_data="check_code")]]
    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Код принял. Нажми кнопку, чтобы проверить.",
        reply_markup=markup,
    )
    return GPT


async def run_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка «Проверить решение» → фиктивный тест."""
    query = update.callback_query
    await query.answer()

    code: str | None = context.user_data.get("user_code")
    if not code:
        await query.edit_message_text("Сначала пришли код решения.")
        return GPT

    await query.edit_message_text("Проверяю решение...")

    ok, report = await run_fake_test(code)

    text = f"{'✅' if ok else '❌'} Решение {'принято' if ok else 'не прошло'}.\n\n{report}"
    await query.edit_message_text(text)

    if ok:
        keyboard = [
            [InlineKeyboardButton("Еще одну задачу!", callback_data="repeat_task")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Решим что-нибудь еще?",
            reply_markup=markup,
        )
        return MAIN_MENU



async def repeat_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    return await start_gpt(update, context)


async def start_modul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Выбери модуль:")

    keyboard = [
        [InlineKeyboardButton("Модуль 1", callback_data="modul_1")],
        [InlineKeyboardButton("Модуль 2", callback_data="modul_2")],
        [InlineKeyboardButton("Модуль 3", callback_data="modul_3")],
        [InlineKeyboardButton("Назад", callback_data="main_menu")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Выберите модуль:",
        reply_markup=markup,
    )

    return MODULS


async def open_modul_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Тема 1", callback_data="topic_1")],
        [InlineKeyboardButton("Тема 2", callback_data="topic_2")],
        [InlineKeyboardButton("Тема 3", callback_data="topic_3")],
        [InlineKeyboardButton("К модулям", callback_data="modul_db")],
        [InlineKeyboardButton("В главное меню", callback_data="main_menu")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text="Модуль 1:\nВыберите тему:", reply_markup=markup)
    return MODULS


async def open_modul_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Тема 1", callback_data="topic_4")],
        [InlineKeyboardButton("Тема 2", callback_data="topic_5")],
        [InlineKeyboardButton("Тема 3", callback_data="topic_6")],
        [InlineKeyboardButton("К модулям", callback_data="modul_db")],
        [InlineKeyboardButton("В главное меню", callback_data="main_menu")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text="Модуль 2:\nВыберите тему:", reply_markup=markup)
    return MODULS


async def open_modul_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Тема 1", callback_data="topic_7")],
        [InlineKeyboardButton("Тема 2", callback_data="topic_8")],
        [InlineKeyboardButton("Тема 3", callback_data="topic_9")],
        [InlineKeyboardButton("К модулям", callback_data="modul_db")],
        [InlineKeyboardButton("В главное меню", callback_data="main_menu")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text="Модуль 3:\nВыберите тему:", reply_markup=markup)
    return MODULS


async def open_topic_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Задача 1", callback_data="task_1_1")],
        [InlineKeyboardButton("Задача 2", callback_data="task_1_2")],
        [InlineKeyboardButton("Задача 3", callback_data="task_1_3")],
        [InlineKeyboardButton("Назад к темам", callback_data="modul_1")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Модуль 1 > Тема 1", reply_markup=markup)
    return MODULS

async def open_topic_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Задача 1", callback_data="task_1_4")],
        [InlineKeyboardButton("Задача 2", callback_data="task_1_5")],
        [InlineKeyboardButton("Задача 3", callback_data="task_1_6")],
        [InlineKeyboardButton("Назад к темам", callback_data="modul_1")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Модуль 1 > Тема 2", reply_markup=markup)
    return MODULS

async def open_topic_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Задача 1", callback_data="task_1_7")],
        [InlineKeyboardButton("Задача 2", callback_data="task_1_8")],
        [InlineKeyboardButton("Задача 3", callback_data="task_1_9")],
        [InlineKeyboardButton("Назад к темам", callback_data="modul_1")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Модуль 1 > Тема 3", reply_markup=markup)
    return MODULS

async def open_topic_4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Задача 1", callback_data="task_2_1")],
        [InlineKeyboardButton("Задача 2", callback_data="task_2_2")],
        [InlineKeyboardButton("Задача 3", callback_data="task_2_3")],
        [InlineKeyboardButton("Назад к темам", callback_data="modul_2")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Модуль 2 > Тема 1", reply_markup=markup)
    return MODULS

async def open_topic_5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Задача 1", callback_data="task_2_4")],
        [InlineKeyboardButton("Задача 2", callback_data="task_2_5")],
        [InlineKeyboardButton("Задача 3", callback_data="task_2_6")],
        [InlineKeyboardButton("Назад к темам", callback_data="modul_2")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Модуль 2 > Тема 2", reply_markup=markup)
    return MODULS

async def open_topic_6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Задача 1", callback_data="task_2_7")],
        [InlineKeyboardButton("Задача 2", callback_data="task_2_8")],
        [InlineKeyboardButton("Задача 3", callback_data="task_2_9")],
        [InlineKeyboardButton("Назад к темам", callback_data="modul_2")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Модуль 2 > Тема 3", reply_markup=markup)
    return MODULS

async def open_topic_7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Задача 1", callback_data="task_3_1")],
        [InlineKeyboardButton("Задача 2", callback_data="task_3_2")],
        [InlineKeyboardButton("Задача 3", callback_data="task_3_3")],
        [InlineKeyboardButton("Назад к темам", callback_data="modul_3")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Модуль 3 > Тема 1", reply_markup=markup)
    return MODULS

async def open_topic_8(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Задача 1", callback_data="task_3_4")],
        [InlineKeyboardButton("Задача 2", callback_data="task_3_5")],
        [InlineKeyboardButton("Задача 3", callback_data="task_3_6")],
        [InlineKeyboardButton("Назад к темам", callback_data="modul_3")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Модуль 3 > Тема 2", reply_markup=markup)
    return MODULS

async def open_topic_9(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Задача 1", callback_data="task_3_7")],
        [InlineKeyboardButton("Задача 2", callback_data="task_3_8")],
        [InlineKeyboardButton("Задача 3", callback_data="task_3_9")],
        [InlineKeyboardButton("Назад к темам", callback_data="modul_3")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Модуль 3 > Тема 3", reply_markup=markup)
    return MODULS