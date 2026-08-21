import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from config.config import TOKEN
from config.states import MAIN_MENU, MODULS, SETTINGS, SOLVING, TOXIC_LEVEL_CHOICE
from db.database import create_tables
from handlers.gpt_handlers import (
    check_solution,
    open_modul,
    open_task,
    open_topic,
    send_hint,
    start_modul,
)
from handlers.main_menu_handlerds import main_menu
from handlers.start_handler import choose_toxic, open_settings, start_handler


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    persistence = PicklePersistence(filepath="conversation_state.pkl")
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(create_tables)
        .persistence(persistence)
        .build()
    )

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={
            TOXIC_LEVEL_CHOICE: [
                CallbackQueryHandler(
                    choose_toxic,
                    pattern="^(low_toxic|medium_toxic|high_toxic)$",
                ),
            ],
            MAIN_MENU: [
                CallbackQueryHandler(start_modul, pattern="modul_db"),
                CallbackQueryHandler(open_settings, pattern="^settings$"),
            ],
            SETTINGS: [
                CallbackQueryHandler(
                    choose_toxic,
                    pattern="^(low_toxic|medium_toxic|high_toxic)$",
                ),
                CallbackQueryHandler(main_menu, pattern="main_menu"),
            ],
            MODULS: [
                CallbackQueryHandler(open_modul, pattern="^modul_[0-9]+$"),
                CallbackQueryHandler(open_topic, pattern="^topic_[0-9]+$"),
                CallbackQueryHandler(open_task, pattern="^task_[0-9]+$"),
                CallbackQueryHandler(start_modul, pattern="modul_db"),
                CallbackQueryHandler(main_menu, pattern="main_menu"),
            ],
            SOLVING: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, check_solution
                ),
                CallbackQueryHandler(send_hint, pattern="^hint$"),
                CallbackQueryHandler(open_modul, pattern="^modul_[0-9]+$"),
                CallbackQueryHandler(open_topic, pattern="^topic_[0-9]+$"),
                CallbackQueryHandler(open_task, pattern="^task_[0-9]+$"),
                CallbackQueryHandler(start_modul, pattern="modul_db"),
                CallbackQueryHandler(main_menu, pattern="main_menu"),
            ],
        },
        fallbacks=[CommandHandler("start", start_handler)],
        persistent=True,
        name="conversation_handler",
    )
    application.add_handler(conversation_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
