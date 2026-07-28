import logging

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config.config import TOKEN
from config.states import GPT, MAIN_MENU
from db.database import create_tables
from handlers.gpt_handlers import (
    check_solution,
    run_check,
    start_gpt,
    start_modul,
)
from handlers.start_handler import start_handler


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)

    application = ApplicationBuilder().token(TOKEN).post_init(create_tables).build()

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(start_gpt, pattern="gpt_ask"),
                CallbackQueryHandler(start_gpt, pattern="start_gpt"),
                CallbackQueryHandler(start_modul, pattern="modul_db"),
            ],
            GPT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_solution),
                CallbackQueryHandler(run_check, pattern="^check_code$"),
            ],
        },
        fallbacks=[CommandHandler("start", start_handler)],
    )

    application.add_handler(conversation_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
