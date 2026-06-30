import asyncio
from openai import AsyncOpenAI
from config.states import GPT
# --- Инициализация клиента (вынесена глобально) ---
client = AsyncOpenAI()

async def start_gpt(update, context):
    query = update.callback_query
    await query.answer() 

    await query.edit_message_text(
        text="Придумываю для тебя новую задачу.",
    )
    asyncio.create_task(generate_and_send_answer(update, context))

    return GPT


async def generate_and_send_answer(update, context):
        status_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Создаю вопросы для контрольной...",
        )
        response = await client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {
                    "role": "system",
                    "content": "Ты — генератор задач по Python."
                },
                {
                    "role": "user",
                    "content": ("Придумай какую-нибудь простенькую задачку на питоне.")
                     
                },
            ],
        )
        answer_text = response.choices[0].message.content

        await context.bot.edit_message_text(
             chat_id=status_msg.chat_id,
             message_id=status_msg.message_id,
             text=answer_text,
        )

#     context: ContextTypes.DEFAULT_TYPE,
#     chat_id: int,
#     message_id: int,
#     m_text: str,
# ):
#     message_history = context.user_data.get("message_history", [])

#     # Чищу историю, чтобы она не разрасталась.
#     if len(message_history) >= 6:
#         message_history.pop(0)
#         message_history.pop(0)

#     # ===========================
#     client = AsyncOpenAI()
#     # ===========================
#     response = await client.responses.create(
#         model="gpt-5-mini",
#         input=[
#             {
#                 "role": "developer",
#                 "content": (
#                     f'Придумай какую-нибудь простинькую задачку на питоне, посмотри примеры задач на https://stepik.org/course/241708/syllabus?auth=login'
#                 ),
#             },
#         ]
#         + message_history
#         + [{"role": "user", "content": m_text}],
#         tools=[{"type": "web_search"}],
#     )
#     answer_text = response.output_text
#     message_history.append({"role": "user", "content": m_text})
#     message_history.append({"role": "assistant", "content": answer_text})
#     context.user_data["message_history"] = message_history

#     keyboard = [[InlineKeyboardButton("Назад", callback_data="back")]]
#     markup = InlineKeyboardMarkup(keyboard)
#     text = "Вот задача, реши её, мне отправь код твоего решения"
#     await context.bot.edit_message_text(
#         chat_id=chat_id,
#         message_id=message_id,
#         text=answer_text,
#         reply_markup=markup,
    


