import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
)

from config.config import TOKEN
from handlers.start_handler import start_handler


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)

    application = ApplicationBuilder().token(TOKEN).build()
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={},
        fallbacks=[CommandHandler("start", start_handler)],
    )
    application.add_handler(conversation_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
