import asyncio
import json
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config.config import ATTEMPTS_PER_DAY, HINTS_PER_DAY
from config.states import MAIN_MENU, MODULS, SOLVING
from db.module_crud import get_module, get_modules
from db.personal_crud import (
    get_set,
    sets_for_user,
    tasks_in_set,
    user_can_open,
    user_can_see_set,
)
from db.topic_crud import get_topic, get_topics_by_module_id
from db.users_crud import get_user
from db.zadacha_crud import (
    add_solution,
    attempts_today,
    hints_today,
    count_solved,
    get_attempt_count,
    get_recent_attempts,
    get_solved_task_ids,
    get_stale_task_ids,
    get_task,
    get_tasks_by_topic,
    next_task_for,
    set_solution_review,
)
from services.code_runner import run_tests
from services.events import track
from services.progress import progress_text
from handlers.offer import maybe_offer_after_solve
from services.tg_html import escape_tg_text, fit_tg_html, prepare_tg_html
from services.verify_python_code import give_hint, review_solution

ROOT = Path(__file__).resolve().parent.parent


def pretty_io(text: str) -> str:
    # если в базе лежит текст с \n как символами — делаем настоящие переносы
    text = text.replace("\\n", "\n").strip()
    return escape_tg_text(text)


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
            parts.append(f"Тест {item['n']}: ❌ слишком долго (больше 5 секунд)")
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


# столько тестов показано в условии задачи; прошедшие скрытые тесты в отчёте не светим
SHOWN_IN_TASK = 3


def format_tests_html(results: list[dict]) -> str:
    parts = []
    for item in results:
        if item.get("ok"):
            if item["n"] <= SHOWN_IN_TASK:
                parts.append(f"<b>Тест {item['n']}:</b> ✅")
        elif item.get("timeout"):
            parts.append(f"<b>Тест {item['n']}:</b> ❌ слишком долго (больше 5 секунд)")
        elif item.get("error"):
            parts.append(
                f"<b>Тест {item['n']}:</b> ❌ ошибка\n"
                f"<code>{escape_tg_text(item['error'])}</code>"
            )
        else:
            parts.append(
                f"<b>Тест {item['n']}:</b> ❌\n"
                f"Ввод:\n<code>{pretty_io(item['input'])}</code>\n"
                f"Ожидалось:\n<code>{pretty_io(item['expected'])}</code>\n"
                f"Получено:\n<code>{pretty_io(item['actual'])}</code>"
            )
    return "\n".join(p if "\n" not in p else "\n" + p for p in parts).strip()


def format_task_text(task: dict) -> str:
    tests = json.loads(task["tests"])[:SHOWN_IN_TASK]
    title = escape_tg_text(task["title"])
    description = escape_tg_text(task["description"])

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
    parts.append(
        "\n\nПиши <code>input()</code> без текста внутри — "
        "подсказка попадёт в вывод и тесты не пройдут.\n"
        "Пришли решение одним сообщением — код на Python."
    )
    return prepare_tg_html("".join(parts), 4096)


async def start_modul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    modules = await get_modules()
    keyboard = []
    for module in modules:
        description = (module.get("description") or "").strip()
        title = f"{module['title']} - {description}" if description else module["title"]
        keyboard.append(
            [
                InlineKeyboardButton(
                    title,
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
    stale_ids = await get_stale_task_ids(user["id"]) if user else set()

    keyboard = []
    for task in tasks:
        title = task["title"]
        style = "primary"
        # решённые — галочка, изменившиеся — перезагрузка
        if task["id"] in solved_ids:
            title = f"✅ {title}"
            style = "success"
        elif task["id"] in stale_ids:
            title = f"🔄 {title}"
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


def task_markup(task: dict, topic_id=None) -> InlineKeyboardMarkup:
    keyboard = []
    set_id = task.get("set_id")
    if set_id:
        keyboard.append(
            [InlineKeyboardButton("К моим задачам", callback_data=f"pset_{set_id}", style="primary")]
        )
    elif topic_id:
        keyboard.append(
            [InlineKeyboardButton("Назад к задачам", callback_data=f"topic_{topic_id}", style="primary")]
        )
    keyboard.append([InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")])
    return InlineKeyboardMarkup(keyboard)


def remember_task(context: ContextTypes.DEFAULT_TYPE, task: dict, topic_id=None):
    context.user_data["task_id"] = task["id"]
    context.user_data.pop("last_code", None)
    context.user_data.pop("last_report", None)
    if task.get("set_id"):
        context.user_data["personal_set_id"] = task["set_id"]
        context.user_data.pop("topic_id", None)
    else:
        context.user_data.pop("personal_set_id", None)
        if topic_id:
            context.user_data["topic_id"] = topic_id
        else:
            context.user_data.pop("topic_id", None)


async def send_task(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user: dict, task: dict, query=None):
    """Показывает условие и переводит в режим решения. С query — правит сообщение, иначе шлёт новое."""
    topic_id = None if task.get("set_id") else context.user_data.get("topic_id")
    remember_task(context, task, topic_id)
    markup = task_markup(task, topic_id)
    text = format_task_text(task)
    image_path = task_image_path(task)
    await track(user["id"], "task_open", {"task_id": task["id"], "cat_key": task.get("cat_key")})

    # картинку нельзя воткнуть в edit_text — шлём фото, потом условие
    if image_path is not None:
        if query is not None:
            try:
                await query.message.delete()
            except TelegramError:
                pass
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=InputFile(image_path.read_bytes(), filename=image_path.name),
            caption=task["title"],
        )
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode="HTML")
        return SOLVING

    if query is not None:
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode="HTML")
    return SOLVING


async def open_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split("_")[1])
    task = await get_task(task_id)
    user = await get_user(update.effective_user.id)
    if not user or not await user_can_open(user["id"], task):
        context.user_data.pop("task_id", None)
        await query.edit_message_text("Этой задачи нет или она не твоя.")
        return MAIN_MENU
    return await send_task(context, query.message.chat_id, user, task, query=query)


async def open_next_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await get_user(update.effective_user.id)
    if not user:
        return MAIN_MENU
    task = await next_task_for(user["id"])
    if task is None:
        await query.message.reply_text("Ты решил вообще всё. Даже мне нечего добавить.")
        return MAIN_MENU
    # новым сообщением: старое с разносом пусть остаётся — его скриншотят
    return await send_task(context, query.message.chat_id, user, task)


def task_image_path(task: dict) -> Path | None:
    rel = task.get("image")
    if not rel:
        return None
    path = ROOT / rel
    if not path.is_file():
        return None
    return path


def result_markup(ok: bool, topic_id, set_id=None) -> InlineKeyboardMarkup:
    keyboard = []
    if ok:
        keyboard.append(
            [InlineKeyboardButton("➡️ Следующая задача", callback_data="next_task", style="success")]
        )
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
    if set_id:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "К моим задачам",
                    callback_data=f"pset_{set_id}",
                    style="primary",
                )
            ]
        )
    elif topic_id:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "К задачам",
                    callback_data=f"topic_{topic_id}",
                    style="primary",
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]
    )
    return InlineKeyboardMarkup(keyboard)


def check_text(attempt_count: int, results: list, ok: bool, feedback: str = "") -> str:
    # тесты короткие (до первого падения), разнос дописывается под ними
    verdict = "✅ Принято" if ok else "❌ Не принято"
    text = f"<b>{verdict} · попытка №{attempt_count}</b>\n\n{format_tests_html(results)}"
    if feedback:
        text += "\n\n" + feedback
    return prepare_tg_html(text, 4096)


async def keep_typing(bot, chat_id: int, stop: asyncio.Event):
    # пока нейронка думает (10–20 с), в чате висит «печатает…» — видно, что разнос едет
    while not stop.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except TelegramError:
            pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=4)
        except asyncio.TimeoutError:
            pass


async def attach_review(
    bot,
    chat_id: int,
    message_id: int,
    ok: bool,
    topic_id,
    set_id,
    attempt_count: int,
    results: list,
    user_code: str,
    condition: str,
    report: str,
    toxic_level: int,
    recent_attempts: list,
    solution_id: int | None = None,
):
    """Разнос дописывается внизу сообщения с тестами, кнопки остаются под ним."""
    stop = asyncio.Event()
    typing = asyncio.create_task(keep_typing(bot, chat_id, stop))
    try:
        feedback = await review_solution(
            user_code,
            condition,
            report,
            toxic_level,
            attempt_count,
            recent_attempts,
            ok,
        )
        if not feedback.strip():
            return
        if solution_id:
            await set_solution_review(solution_id, feedback)
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=check_text(attempt_count, results, ok, feedback),
            parse_mode="HTML",
            reply_markup=None if ok else result_markup(ok, topic_id, set_id),
        )
    except Exception:
        logging.getLogger(__name__).exception("ревью не дописалось")
    finally:
        stop.set()
        await typing


async def check_solution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get("task_id")
    if not task_id:
        await update.message.reply_text("Сначала выбери задачу в меню.")
        return MAIN_MENU

    task = await get_task(task_id)
    user = await get_user(update.effective_user.id)
    if not user or not await user_can_open(user["id"], task):
        await update.message.reply_text("Эта задача не твоя или её уже нет.")
        return MAIN_MENU

    if await attempts_today(user["id"]) >= ATTEMPTS_PER_DAY:
        await update.message.reply_text(
            f"На сегодня всё: {ATTEMPTS_PER_DAY} попыток за сутки. "
            "Отдохни, завтра разнесу с новыми силами."
        )
        return SOLVING

    lock = user_lock(user["id"])
    if lock.locked():
        await update.message.reply_text("Подожди, ещё проверяю прошлый код.")
        return SOLVING

    async with lock:
        return await _check_solution(update, context, task, user)


# одна проверка на пользователя за раз: иначе флуд кодом плодит контейнеры
_user_locks: dict[int, asyncio.Lock] = {}


def user_lock(user_id: int) -> asyncio.Lock:
    lock = _user_locks.get(user_id)
    if lock is None:
        lock = _user_locks[user_id] = asyncio.Lock()
    return lock


async def _check_solution(update: Update, context: ContextTypes.DEFAULT_TYPE, task: dict, user: dict):
    task_id = task["id"]
    # Убираем кривые кавычки, заменяя из на обычные
    user_code = fix_quotes(update.message.text)
    wait = await update.message.reply_text("Проверяю решение...")

    tests = json.loads(task["tests"])
    ok, results = await run_tests(user_code, tests)
    if results and results[0].get("infra"):
        # сломалась песочница, а не решение — попытку не засчитываем
        await wait.edit_text(
            "Проверка сейчас не работает — это у нас, а не у тебя. "
            "Попробуй прислать код ещё раз через минуту."
        )
        return SOLVING
    report = format_tests_plain(results)

    solved_before = await count_solved(user["id"])
    solution_id = await add_solution(
        user["id"], task_id, user_code, "ok" if ok else "fail", results
    )
    await track(
        user["id"],
        "solved" if ok else "submit_fail",
        {"task_id": task_id, "cat_key": task.get("cat_key")},
    )
    attempt_count = await get_attempt_count(user["id"], task_id)
    recent_attempts = await get_recent_attempts(user["id"], task_id)
    context.user_data["last_code"] = user_code
    context.user_data["last_report"] = report

    set_id = task.get("set_id")
    topic_id = None if set_id else context.user_data.get("topic_id")
    markup = result_markup(ok, topic_id, set_id)
    text = check_text(attempt_count, results, ok)

    # тесты сразу, разнос через 10–20 с допишется внизу этого же сообщения
    if ok:
        solved_now = await count_solved(user["id"])
        await wait.edit_text(text, parse_mode="HTML")
        done = "Задача решена."
        if solved_now > solved_before:
            done += "\n" + progress_text(solved_before, solved_now)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=done,
            reply_markup=markup,
        )
        await maybe_offer_after_solve(context.bot, user, update.effective_chat.id, solved_now)
    else:
        await wait.edit_text(text, reply_markup=markup, parse_mode="HTML")

    asyncio.create_task(
        attach_review(
            context.bot,
            update.effective_chat.id,
            wait.message_id,
            ok,
            topic_id,
            set_id,
            attempt_count,
            results,
            user_code,
            task["description"],
            report,
            user["toxic_level"],
            recent_attempts,
            solution_id,
        )
    )
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

    task = await get_task(task_id)
    user = await get_user(update.effective_user.id)
    if not user or not await user_can_open(user["id"], task):
        await query.message.reply_text("Эта задача не твоя или её уже нет.")
        return SOLVING

    if await hints_today(user["id"]) >= HINTS_PER_DAY:
        await query.message.reply_text(
            f"Подсказок на сегодня больше нет — было {HINTS_PER_DAY}. Попробуй сам, ты ближе, чем думаешь."
        )
        return SOLVING

    await track(user["id"], "hint", {"task_id": task_id})
    wait = await query.message.reply_text("Думаю над подсказкой...")
    attempt_count = await get_attempt_count(user["id"], task_id)
    recent_attempts = await get_recent_attempts(user["id"], task_id)

    try:
        hint = await give_hint(
            code,
            task["description"],
            report or "",
            user["toxic_level"],
            attempt_count,
            recent_attempts,
        )
    except Exception:
        logging.getLogger(__name__).exception("подсказка не пришла")
        await wait.edit_text("Нейронка сейчас не отвечает. Нажми «Дай подсказку» ещё раз через минуту.")
        return SOLVING
    hint = fit_tg_html(hint or "Подсказка вышла пустой — нажми ещё раз.", 4000)
    await wait.edit_text(hint, parse_mode="HTML")
    return SOLVING


def clip_button(title: str) -> str:
    # у кнопки в телеграме короткий лимит, длинное название обрезаем
    if len(title) <= 48:
        return title
    return title[:45] + "..."


async def open_personal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = await get_user(update.effective_user.id)
    sets = await sets_for_user(user["id"]) if user else []
    back = InlineKeyboardMarkup(
        [[InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]]
    )
    if not sets:
        await query.edit_message_text("Персональных заданий пока нет.", reply_markup=back)
        return MAIN_MENU

    solved_ids = await get_solved_task_ids(user["id"])
    keyboard = []
    for personal in sets:
        tasks = await tasks_in_set(personal["id"])
        done = sum(1 for task in tasks if task["id"] in solved_ids)
        label = f"{clip_button(personal['title'])} ({done}/{len(tasks)})"
        keyboard.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"pset_{personal['id']}",
                    style="primary",
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]
    )
    await query.edit_message_text(
        "Персональные задания.\nВыбери блок:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return MODULS


async def open_personal_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    set_id = int(query.data.split("_")[1])
    user = await get_user(update.effective_user.id)
    personal = await get_set(set_id)
    if not user or not personal or not await user_can_see_set(user["id"], set_id):
        await query.edit_message_text("Этот блок не твой.")
        return MAIN_MENU

    tasks = await tasks_in_set(set_id)
    solved_ids = await get_solved_task_ids(user["id"])
    stale_ids = await get_stale_task_ids(user["id"])
    keyboard = []
    for task in tasks:
        title = clip_button(task["title"])
        style = "primary"
        if task["id"] in solved_ids:
            title = f"✅ {title}"
            style = "success"
        elif task["id"] in stale_ids:
            title = f"🔄 {title}"
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
        [InlineKeyboardButton("К блокам", callback_data="personal", style="primary")]
    )
    keyboard.append(
        [InlineKeyboardButton("В меню", callback_data="main_menu", style="primary")]
    )
    if tasks:
        text = f"{personal['title']}\nВыбери задачу:"
    else:
        text = f"{personal['title']}\nПока пусто — задачи ещё не добавили."
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return MODULS
