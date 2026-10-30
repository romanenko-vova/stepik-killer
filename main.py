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

from admin.app import start_admin
from config.config import STATE_PATH, TOKEN
from config.states import MAIN_MENU, MODULS, SETTINGS, SOLVING, TOXIC_LEVEL_CHOICE
from db.database import on_startup as db_startup
from handlers.gpt_handlers import (
    check_solution,
    open_modul,
    open_next_task,
    open_personal,
    open_personal_set,
    open_task,
    open_topic,
    send_hint,
    start_modul,
)
from handlers.main_menu_handlerds import main_menu
from handlers.start_handler import choose_toxic, open_settings, settings_command, start_handler


async def on_startup(app):
    await db_startup()
    await start_admin()


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    persistence = PicklePersistence(filepath=STATE_PATH)
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        # не в скобки билдера — это метод цепочки, иначе TypeError
        .concurrent_updates(True)
        .post_init(on_startup)
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
                CallbackQueryHandler(open_next_task, pattern="^next_task$"),
                CallbackQueryHandler(start_modul, pattern="modul_db"),
                CallbackQueryHandler(open_personal, pattern="^personal$"),
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
                CallbackQueryHandler(open_next_task, pattern="^next_task$"),
                CallbackQueryHandler(open_modul, pattern="^modul_[0-9]+$"),
                CallbackQueryHandler(open_topic, pattern="^topic_[0-9]+$"),
                CallbackQueryHandler(open_task, pattern="^task_[0-9]+$"),
                CallbackQueryHandler(open_personal, pattern="^personal$"),
                CallbackQueryHandler(open_personal_set, pattern="^pset_[0-9]+$"),
                CallbackQueryHandler(start_modul, pattern="modul_db"),
                CallbackQueryHandler(main_menu, pattern="main_menu"),
            ],
            SOLVING: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, check_solution
                ),
                CallbackQueryHandler(send_hint, pattern="^hint$"),
                CallbackQueryHandler(open_next_task, pattern="^next_task$"),
                CallbackQueryHandler(open_modul, pattern="^modul_[0-9]+$"),
                CallbackQueryHandler(open_topic, pattern="^topic_[0-9]+$"),
                CallbackQueryHandler(open_task, pattern="^task_[0-9]+$"),
                CallbackQueryHandler(open_personal, pattern="^personal$"),
                CallbackQueryHandler(open_personal_set, pattern="^pset_[0-9]+$"),
                CallbackQueryHandler(start_modul, pattern="modul_db"),
                CallbackQueryHandler(main_menu, pattern="main_menu"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start_handler),
            CommandHandler("settings", settings_command),
        ],
        persistent=True,
        name="conversation_handler",
    )
    application.add_handler(conversation_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
