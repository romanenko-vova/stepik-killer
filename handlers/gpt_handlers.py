import asyncio

from openai import AsyncOpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config.states import GPT, MAIN_MENU
from db.zadacha_crud import add_task
from services.code_runner import run_fake_test


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
    # просто запоминаем код и даём кнопку проверки
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

    code = context.user_data.get("user_code")
    if not code:
        await query.edit_message_text("Сначала пришли код решения.")
        return GPT

    await query.edit_message_text("Проверяю решение...")

    ok, report = await run_fake_test(code)

    if ok:
        text = f"✅ Решение принято!\n\n{report}"
    else:
        text = f"❌ Решение не прошло.\n\n{report}"

    await query.edit_message_text(text)

    if ok:
        keyboard = [
            [InlineKeyboardButton("Еще одну задачу!", callback_data="start_gpt")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Решим что-нибудь еще?",
            reply_markup=markup,
        )
        return MAIN_MENU

    return GPT


async def start_modul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
