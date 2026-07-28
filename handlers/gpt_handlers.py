import asyncio

from openai import AsyncOpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config.states import GPT, MAIN_MENU,MODULS
from services.verify_python_code import verify_python_code
from db.zadacha_crud import add_task


async def start_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(text="Придумываю для тебя новую задачу.")
    asyncio.create_task(generate_and_send_answer(update, context))
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
    await add_task(
        "Задача",
        "списки",
        1,
        answer_text,
        '[{"input_text":"1 1", "output_text": "2"}, {"input_text":"2 2", "output_text": "4"}]',
    )

    context.user_data["current_task"] = {
        "condition": answer_text,
    }


async def check_solution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_code = update.effective_message.text

    checking_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Проверяю твой код..."
    )

    condition = context.user_data["current_task"]["condition"]

    is_correct, feedback = await verify_python_code(user_code, condition)

    verdict = "Твой код верный!\n\n" if is_correct else "В коде есть ошибки.\n\n"
    final_text = f"{verdict}Комментарии:\n{feedback}"

    await context.bot.edit_message_text(
        chat_id=checking_msg.chat_id,
        message_id=checking_msg.message_id,
        text=final_text,
    )
    if is_correct:
        keyboard = [
            [InlineKeyboardButton("Еще одну задачу!", callback_data="start_gpt_povtor")]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Решим что-нибудь еще?",
            reply_markup=markup,
        )

        return MAIN_MENU
    
async def start_modul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Выбери")

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
        [InlineKeyboardButton("Тема 1", callback_data="topic_1_1")],
        [InlineKeyboardButton("Тема 2", callback_data="topic_1_2")],
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
        [InlineKeyboardButton("Тема 1", callback_data="topic_2_1")],
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
        [InlineKeyboardButton("Тема 1", callback_data="topic_3_1")],
        [InlineKeyboardButton("К модулям", callback_data="modul_db")],
        [InlineKeyboardButton("В главное меню", callback_data="main_menu")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text="Модуль 3:\nВыберите тему:", reply_markup=markup)
    return MODULS