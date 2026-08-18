import html
import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config.states import MAIN_MENU, MODULS, SOLVING
from db.module_crud import get_module, get_modules
from db.topic_crud import get_topic, get_topics_by_module_id
from db.users_crud import get_user
from db.zadacha_crud import (
    add_solution,
    get_attempt_count,
    get_recent_attempts,
    get_solved_task_ids,
    get_task,
    get_tasks_by_topic,
)
from services.code_runner import run_tests
from services.tg_html import fit_tg_html
from services.verify_python_code import give_hint, review_solution


def pretty_io(text: str) -> str:
    # если в базе лежит текст с \n как символами — делаем настоящие переносы
    text = text.replace("\\n", "\n").strip()
    return html.escape(text)


def fix_quotes(code: str) -> str:
    # в тг часто прилетают фигурные кавычки, питон их не понимает
    return code.replace("‘", "'").replace("’", "'")


def format_tests_plain(results: list[dict]) -> str:
    # для gpt — обычный текст, тоже с нормальными переносами
    parts = []
    for item in results:
        if item.get("ok"):
            parts.append(f"Тест {item['n']}: ✅")
        elif item.get("timeout"):
            parts.append(f"Тест {item['n']}: ❌ слишком долго (больше 10 секунд)")
        elif item.get("error"):
            parts.append(f"Тест {item['n']}: ❌ ошибка\n{item['error']}")
        else:
            inp = item["input"].replace("\\n", "\n").strip()
            exp = item["expected"].replace("\\n", "\n").strip()
            got = item["actual"].replace("\\n", "\n").strip()
            parts.append(
                f"Тест {item['n']}: ❌\n"
                f"Ввод:\n{inp}\n"
                f"Ожидалось:\n{exp}\n"
                f"Получено:\n{got}"
            )
    return "\n\n".join(parts)


def format_tests_html(results: list[dict]) -> str:
    parts = []
    for item in results:
        if item.get("ok"):
            parts.append(f"<b>Тест {item['n']}:</b> ✅")
        elif item.get("timeout"):
            parts.append(f"<b>Тест {item['n']}:</b> ❌ слишком долго (больше 10 секунд)")
        elif item.get("error"):
            parts.append(
                f"<b>Тест {item['n']}:</b> ❌ ошибка\n"
                f"<code>{html.escape(item['error'])}</code>"
            )
        else:
            parts.append(
                f"<b>Тест {item['n']}:</b> ❌\n"
                f"Ввод:\n<code>{pretty_io(item['input'])}</code>\n"
                f"Ожидалось:\n<code>{pretty_io(item['expected'])}</code>\n"
                f"Получено:\n<code>{pretty_io(item['actual'])}</code>"
            )
    return "\n\n".join(parts)


def format_task_text(task: dict) -> str:
    tests = json.loads(task["tests"])[:3]
    title = html.escape(task["title"])
    description = html.escape(task["description"])

    parts = [
        f"<b>{title}</b>\n\n",
        f"{description}\n\n",
        "<b>Примеры тестов</b>",
    ]
    for i, test in enumerate(tests, 1):
        parts.append(
            f"\n\n<b>Тест {i}</b>\n"
            f"Ввод:\n<code>{pretty_io(test['input'])}</code>\n"
            f"Вывод:\n<code>{pretty_io(test['expected'])}</code>"
        )
    parts.append("\n\nПришли решение одним сообщением — код на Python.")
    return "".join(parts)


async def start_modul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    modules = await get_modules()
    keyboard = []
    for module in modules:
        keyboard.append(
            [
                InlineKeyboardButton(
                    module["title"],
                    callback_data=f"modul_{module['id']}",
                    style="primary",
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]
    )
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Выберите модуль:",
        reply_markup=markup,
    )
    return MODULS


async def open_modul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    module_id = int(query.data.split("_")[1])
    context.user_data["module_id"] = module_id

    module = await get_module(module_id)
    topics = await get_topics_by_module_id(module_id)

    keyboard = []
    for topic in topics:
        keyboard.append(
            [
                InlineKeyboardButton(
                    topic["title"],
                    callback_data=f"topic_{topic['id']}",
                    style="primary",
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("К модулям", callback_data="modul_db", style="primary")]
    )
    keyboard.append(
        [InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]
    )
    markup = InlineKeyboardMarkup(keyboard)

    title = module["title"] if module else "Модуль"
    await query.edit_message_text(
        text=f"{title}\nВыберите тему:",
        reply_markup=markup,
    )
    return MODULS


async def open_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    topic_id = int(query.data.split("_")[1])
    context.user_data["topic_id"] = topic_id

    topic = await get_topic(topic_id)
    tasks = await get_tasks_by_topic(topic["title"])
    module_id = topic["module_id"]
    context.user_data["module_id"] = module_id

    user = await get_user(update.effective_user.id)
    solved_ids = await get_solved_task_ids(user["id"]) if user else set()

    keyboard = []
    for task in tasks:
        title = task["title"]
        style = "primary"
        # решённые красим зелёным и ставим галочку
        if task["id"] in solved_ids:
            title = f"✅ {title}"
            style = "success"
        keyboard.append(
            [
                InlineKeyboardButton(
                    title,
                    callback_data=f"task_{task['id']}",
                    style=style,
                )
            ]
        )
    keyboard.append(
        [
            InlineKeyboardButton(
                "Назад к темам",
                callback_data=f"modul_{module_id}",
                style="primary",
            )
        ]
    )
    keyboard.append(
        [InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]
    )
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"{topic['title']}\nВыберите задачу:",
        reply_markup=markup,
    )
    return MODULS


async def open_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split("_")[1])
    task = await get_task(task_id)
    context.user_data["task_id"] = task_id

    topic_id = context.user_data.get("topic_id")
    keyboard = []
    if topic_id:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "Назад к задачам",
                    callback_data=f"topic_{topic_id}",
                    style="primary",
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]
    )
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=format_task_text(task),
        reply_markup=markup,
        parse_mode="HTML",
    )
    return SOLVING


async def check_solution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get("task_id")
    if not task_id:
        await update.message.reply_text("Сначала выбери задачу в меню.")
        return MAIN_MENU

    user_code = fix_quotes(update.message.text)
    wait = await update.message.reply_text("Проверяю решение...")

    task = await get_task(task_id)
    tests = json.loads(task["tests"])
    ok, results = await run_tests(user_code, tests)
    report = format_tests_plain(results)

    user = await get_user(update.effective_user.id)
    await add_solution(user["id"], task_id, user_code, "ok" if ok else "fail")
    attempt_count = await get_attempt_count(user["id"], task_id)
    recent_attempts = await get_recent_attempts(user["id"], task_id)
    context.user_data["last_code"] = user_code
    context.user_data["last_report"] = report

    # тесты уже прогнались — gpt смотрит код и отчёт, орёт в выбранном тоне
    feedback = await review_solution(
        user_code,
        task["description"],
        report,
        user["toxic_level"],
        attempt_count,
        recent_attempts,
        ok,
    )

    head = (
        f"<b>Попытка №{attempt_count}</b>\n\n"
        f"<b>Тесты</b>\n{format_tests_html(results)}\n\n"
    )
    tail = ""
    if not ok:
        tail = "\n\nМожешь прислать исправленный код сам или нажать «Дай подсказку»."
    feedback = fit_tg_html(feedback, max(400, 4000 - len(head) - len(tail)))
    text = head + feedback + tail

    topic_id = context.user_data.get("topic_id")
    keyboard = []
    if not ok:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "💡 Дай подсказку",
                    callback_data="hint",
                    style="primary",
                )
            ]
        )
    if topic_id:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "К задачам",
                    callback_data=f"topic_{topic_id}",
                    style="success" if ok else "primary",
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]
    )
    markup = InlineKeyboardMarkup(keyboard)

    # успех не затираем кнопками — результат остаётся, меню уходит новым сообщением
    if ok:
        await wait.edit_text(text, parse_mode="HTML")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Задача решена. Что дальше?",
            reply_markup=markup,
        )
    else:
        await wait.edit_text(text, reply_markup=markup, parse_mode="HTML")
    return SOLVING


async def send_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    task_id = context.user_data.get("task_id")
    code = context.user_data.get("last_code")
    report = context.user_data.get("last_report")
    if not task_id or not code:
        await query.message.reply_text("Сначала пришли решение.")
        return SOLVING

    wait = await query.message.reply_text("Думаю над подсказкой...")
    task = await get_task(task_id)
    user = await get_user(update.effective_user.id)
    attempt_count = await get_attempt_count(user["id"], task_id)
    recent_attempts = await get_recent_attempts(user["id"], task_id)

    hint = await give_hint(
        code,
        task["description"],
        report or "",
        user["toxic_level"],
        attempt_count,
        recent_attempts,
    )
    hint = fit_tg_html(hint, 4000)
    await wait.edit_text(hint, parse_mode="HTML")
    return SOLVING
