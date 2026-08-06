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
from config.states import GPT, MAIN_MENU, MODULS
from db.database import create_tables
from handlers.gpt_handlers import (
    check_solution,
    open_modul_1,
    open_modul_2,
    open_modul_3,
    open_topic,
    run_check,
    start_gpt,
    start_modul,
)
from handlers.main_menu_handlerds import main_menu
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
                CallbackQueryHandler(start_gpt, pattern="repeat_task"),
                CallbackQueryHandler(start_modul, pattern="modul_db"),
            ],
            GPT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_solution),
                CallbackQueryHandler(run_check, pattern="^check_code$"),
            ],
            MODULS: [
                CallbackQueryHandler(open_modul_1, pattern="modul_[0-9]+"),
                CallbackQueryHandler(open_modul_2, pattern="modul_2"),
                CallbackQueryHandler(open_modul_3, pattern="modul_3"),
                CallbackQueryHandler(main_menu, pattern="main_menu"),
                # ==============================================================
                CallbackQueryHandler(open_topic, pattern="^topic_[0-9]+$"),
            
            ],
        },
        fallbacks=[CommandHandler("start", start_handler)],
    )

    application.add_handler(CallbackQueryHandler(check_solution, pattern="^task_.*$"))

    application.add_handler(conversation_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
