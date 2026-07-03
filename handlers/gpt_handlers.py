
import asyncio
from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.states import GPT

client = AsyncOpenAI()

async def start_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    await query.edit_message_text(text="Придумываю для тебя новую задачу.")
    asyncio.create_task(generate_and_send_answer(update, context))
    return GPT.WAIT_SOLUTION

async def generate_and_send_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Создаю вопросы для контрольной...",
    )
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[
            {"role": "system", "content": "Ты — генератор задач по Python."},
            {"role": "user", "content": "Придумай простенькую задачку на питоне. В конце напиши 'Напиши мне решение этой задачи'."}
        ],
    )
    
    answer_text = response.choices[0].message.content.strip()
    
    task_message = await context.bot.edit_message_text(
         chat_id=status_msg.chat_id,
         message_id=status_msg.message_id,
         text=answer_text,
    )
    
    context.user_data['current_task'] = {
        'chat_id': task_message.chat_id,
        'task_message_id': task_message.message_id,
    }

async def check_solution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_code = update.message.text.strip()
    
    checking_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Проверяю твой код..."
    )
    
    condition = "Реши задачу, которую я прислал ранее."
    
    is_correct, feedback = await verify_python_code(user_code, condition)
    
    verdict = "Твой код верный!\n\n" if is_correct else "В коде есть ошибки.\n\n"
    final_text = f"{verdict}Комментарии:\n{feedback}"

    await context.bot.edit_message_text(
        chat_id=checking_msg.chat_id,
        message_id=checking_msg.message_id,
        text=final_text,
    )
    
    keyboard = [[InlineKeyboardButton("Еще одну задачу!", callback_data="start_gpt")]]
    markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Решим что-нибудь еще?",
        reply_markup=markup
    )
    
    return ConversationHandler.END

async def verify_python_code(code: str, condition: str):
    prompt = f"""
УСЛОВИЕ:
{condition}

КОД:
Верно ли он работает? Ответь коротко (Да/Нет) и объясни почему.
"""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    
    result_text = response.choices[0].message.content.strip()
    
    if result_text.startswith("Да"):
        return True, result_text
        
    return False, result_text