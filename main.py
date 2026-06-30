import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
)

from config.config import TOKEN
from config.states import MAIN_MENU,GPT
from handlers.start_handler import start_handler
from handlers.gpt_handlers import start_gpt,generate_and_send_answer


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)

    application = ApplicationBuilder().token(TOKEN).build()
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(start_gpt, pattern="gpt_ask"),
            ],
            GPT: [
                CallbackQueryHandler(generate_and_send_answer, pattern="generate_and_send_answer"),
            ],
            
        },
        fallbacks=[CommandHandler("start", start_handler)],
    )
    application.add_handler(conversation_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
