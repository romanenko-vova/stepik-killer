
import asyncio

from openai import AsyncOpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config.states import GPT, MAIN_MENU
from services.verify_python_code import verify_python_code


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
            {"role": "user", "content": "Придумай простенькую задачку на питоне. В конце напиши 'Напиши мне решение этой задачи'."}
        ],
    )
    
    answer_text = response.output_text
    
    query = update.callback_query
    await query.edit_message_text(text=answer_text)
    
    context.user_data['current_task'] = {
        'condition': answer_text,
    }
    

async def check_solution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_code = update.effective_message.text
    
    checking_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Проверяю твой код..."
    )
    
    condition = context.user_data['current_task']['condition']
    
    is_correct, feedback = await verify_python_code(user_code, condition)
    
    
    verdict = "Твой код верный!\n\n" if is_correct else "В коде есть ошибки.\n\n"
    final_text = f"{verdict}Комментарии:\n{feedback}"

    await context.bot.edit_message_text(
        chat_id=checking_msg.chat_id,
        message_id=checking_msg.message_id,
        text=final_text,
    )
    if is_correct:
        keyboard = [[InlineKeyboardButton("Еще одну задачу!", callback_data="start_gpt")]]
        markup = InlineKeyboardMarkup(keyboard)
    
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Решим что-нибудь еще?",
            reply_markup=markup
        )
        
        return MAIN_MENU


