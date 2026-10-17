import html
import json

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from admin.app import mark_label, page, require_admin
from db.admin_crud import person_name
from db.personal_crud import (
    all_sets,
    create_personal_task,
    create_set,
    delete_personal_task,
    delete_set,
    get_set,
    normalize_tests,
    tasks_with_status,
    update_personal_task,
    update_set_title,
)
from db.users_crud import get_user_by_id, list_users
from db.zadacha_crud import get_task

router = APIRouter()

TEST_JS = """
<script>
function addTest() {
  const tpl = document.getElementById("test-template");
  const node = tpl.content.cloneNode(true);
  document.getElementById("tests").appendChild(node);
}
</script>
"""

TEST_TEMPLATE = """
<template id="test-template">
  <div class="card test-row">
    <label>Ввод <span class="meta">что программа читает через input. Можно несколько строк.</span></label>
    <textarea name="test_input"></textarea>
    <label>Ожидаемый вывод</label>
    <textarea name="test_expected"></textarea>
    <p><button type="button" class="ghost" onclick="this.closest('.test-row').remove()">Убрать тест</button></p>
  </div>
</template>
"""


def _form_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _difficulty(raw: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1
    if value not in (1, 2, 3):
        return 1
    return value


def _test_fields(tests: list[dict]) -> str:
    if not tests:
        tests = [{"input": "", "expected": ""}]
    parts = []
    for test in tests:
        parts.append(
            "<div class='card test-row'>"
            "<label>Ввод <span class='meta'>что программа читает через input. Можно несколько строк.</span></label>"
            f"<textarea name='test_input'>{html.escape(test.get('input') or '')}</textarea>"
            "<label>Ожидаемый вывод</label>"
            f"<textarea name='test_expected'>{html.escape(test.get('expected') or '')}</textarea>"
            "<p><button type='button' class='ghost' onclick=\"this.closest('.test-row').remove()\">Убрать тест</button></p>"
            "</div>"
        )
    return "".join(parts)


def task_form(
    set_id: int,
    *,
    task: dict | None = None,
    error: str = "",
    tests: list[dict] | None = None,
    title: str = "",
    description: str = "",
    difficulty: int = 1,
) -> str:
    if task and tests is None:
        tests = json.loads(task["tests"])
        title = task["title"]
        description = task["description"]
        difficulty = task["difficulty"]
    action = (
        f"/personal/{set_id}/task/{task['id']}"
        if task
        else f"/personal/{set_id}/task/new"
    )
    options = []
    for value, label in (
        (1, "1 — легко"),
        (2, "2 — обычно"),
        (3, "3 — сложнее"),
    ):
        selected = " selected" if value == difficulty else ""
        options.append(f"<option value='{value}'{selected}>{label}</option>")
    err = f"<p class='fail'>{html.escape(error)}</p>" if error else ""
    heading = "Править задачу" if task else "Новая задача"
    return (
        f"<h2>{heading}</h2>"
        f"{err}"
        f"<form method='post' action='{action}'>"
        "<label>Название</label>"
        f"<input type='text' name='title' value='{html.escape(title)}' required>"
        "<label>Условие</label>"
        f"<textarea name='description' required>{html.escape(description)}</textarea>"
        "<label>Сложность</label>"
        f"<select name='difficulty'>{''.join(options)}</select>"
        "<h3>Тесты</h3>"
        "<p class='meta'>Пустую пару не сохраняю. Если программа ничего не печатает — оставь вывод пустым, но ввод напиши.</p>"
        f"<div id='tests'>{_test_fields(tests or [])}</div>"
        "<p><button type='button' class='ghost' onclick='addTest()'>Ещё тест</button></p>"
        f"{TEST_TEMPLATE}"
        "<p><button type='submit'>Сохранить задачу</button></p>"
        "</form>"
        f"{TEST_JS}"
    )


@router.get("/personal", response_class=HTMLResponse)
async def personal_index(_: str = Depends(require_admin)):
    sets = await all_sets()
    if not sets:
        rows = "<p>Блоков пока нет. Создай первый — и ученик увидит его в боте.</p>"
    else:
        body_rows = []
        for item in sets:
            name = html.escape(person_name(item))
            title = html.escape(item["title"])
            body_rows.append(
                "<tr>"
                f"<td><a href='/personal/{item['id']}'>{title}</a></td>"
                f"<td><a href='/u/{item['user_id']}'>{name}</a></td>"
                f"<td>{item['task_count']}</td>"
                "</tr>"
            )
        rows = (
            "<table><thead><tr><th>Блок</th><th>Ученик</th><th>Задач</th></tr></thead><tbody>"
            + "".join(body_rows)
            + "</tbody></table>"
        )
    body = (
        "<p><a class='btn' href='/personal/new'>Новый блок</a></p>"
        "<p class='meta'>Блок видит только выбранный ученик. В общем курсе эти задачи не появляются.</p>"
        + rows
    )
    return page("Персональные задания", body)


@router.get("/personal/new", response_class=HTMLResponse)
async def new_set_form(user: int | None = None, _: str = Depends(require_admin)):
    return page("Новый блок", await _set_form(user))


@router.post("/personal/new")
async def new_set(
    user_id: int = Form(),
    title: str = Form(""),
    _: str = Depends(require_admin),
):
    title = title.strip()
    student = await get_user_by_id(user_id)
    if not student or not title:
        page_html = await _set_form(user_id, title, "Выбери ученика и напиши название блока.")
        return HTMLResponse(page("Новый блок", page_html), status_code=400)
    set_id = await create_set(user_id, title)
    return RedirectResponse(f"/personal/{set_id}", status_code=303)


async def _set_form(user_id: int | None, title: str = "", error: str = "") -> str:
    users = await list_users()
    if not users:
        return "<p>Сначала ученик должен написать боту /start. Пока в базе никого нет.</p>"
    options = ["<option value=''>выбери ученика</option>"]
    for user in users:
        selected = " selected" if user_id and user["id"] == user_id else ""
        label = html.escape(person_name(user))
        if user.get("username"):
            label += f" (@{html.escape(user['username'])})"
        options.append(f"<option value='{user['id']}'{selected}>{label}</option>")
    err = f"<p class='fail'>{html.escape(error)}</p>" if error else ""
    return (
        "<p><a href='/personal'>← все блоки</a></p>"
        "<h2>Новый блок</h2>"
        f"{err}"
        "<form method='post' action='/personal/new'>"
        "<label>Ученик</label>"
        f"<select name='user_id' required>{''.join(options)}</select>"
        "<label>Название блока</label>"
        f"<input type='text' name='title' value='{html.escape(title)}' required placeholder='Например: Александру перед контрольной'>"
        "<p class='meta'>Это название ученик увидит кнопкой в боте. Лучше коротко.</p>"
        "<p><button type='submit'>Создать блок</button></p>"
        "</form>"
    )


@router.get("/personal/{set_id}", response_class=HTMLResponse)
async def set_page(set_id: int, saved: int = 0, _: str = Depends(require_admin)):
    personal = await get_set(set_id)
    if not personal:
        raise HTTPException(404, "Нет такого блока")
    student = await get_user_by_id(personal["user_id"])
    tasks = await tasks_with_status(set_id, personal["user_id"])
    rows = []
    for task in tasks:
        rows.append(
            "<tr>"
            f"<td><a href='/personal/{set_id}/task/{task['id']}'>{html.escape(task['title'])}</a></td>"
            f"<td>{mark_label(task['mark'])}</td>"
            f"<td>{task['attempts']}</td>"
            f"<td>{html.escape(str(task['last_try'] or '—'))}</td>"
            "</tr>"
        )
    table = (
        "<table><thead><tr><th>Задача</th><th>Статус</th><th>Попыток</th><th>Последняя</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        if rows
        else "<p>В блоке пока нет задач.</p>"
    )
    note = "<p class='ok'>Сохранил.</p>" if saved else ""
    name = html.escape(person_name(student)) if student else "ученик"
    body = (
        "<p><a href='/personal'>← все блоки</a></p>"
        f"{note}"
        f"<h2>{html.escape(personal['title'])}</h2>"
        f"<p class='meta'>Для <a href='/u/{personal['user_id']}'>{name}</a>. "
        "В боте блок появится в «Персональные задания», как только ученик откроет меню.</p>"
        "<form method='post' action='/personal/"
        f"{set_id}/title' class='inline'>"
        "<label>Название</label>"
        f"<input type='text' name='title' value='{html.escape(personal['title'])}' required>"
        "<p><button type='submit'>Переименовать</button></p>"
        "</form>"
        f"<p><a class='btn' href='/personal/{set_id}/task/new'>Добавить задачу</a></p>"
        + table
        + "<form method='post' action='/personal/"
        f"{set_id}/delete' onsubmit=\"return confirm('Удалить блок и все задачи в нём?')\">"
        "<p><button type='submit' class='danger'>Удалить блок</button></p>"
        "</form>"
    )
    return page(personal["title"], body)


@router.post("/personal/{set_id}/title")
async def rename_set(
    set_id: int,
    title: str = Form(""),
    _: str = Depends(require_admin),
):
    personal = await get_set(set_id)
    if not personal:
        raise HTTPException(404, "Нет такого блока")
    title = title.strip()
    if title:
        await update_set_title(set_id, title)
    return RedirectResponse(f"/personal/{set_id}?saved=1", status_code=303)


@router.post("/personal/{set_id}/delete")
async def remove_set(set_id: int, _: str = Depends(require_admin)):
    await delete_set(set_id)
    return RedirectResponse("/personal", status_code=303)


@router.get("/personal/{set_id}/task/new", response_class=HTMLResponse)
async def new_task_form(set_id: int, _: str = Depends(require_admin)):
    personal = await get_set(set_id)
    if not personal:
        raise HTTPException(404, "Нет такого блока")
    body = (
        f"<p><a href='/personal/{set_id}'>← {html.escape(personal['title'])}</a></p>"
        + task_form(set_id)
    )
    return page("Новая задача", body)


@router.post("/personal/{set_id}/task/new", response_class=HTMLResponse)
async def new_task(
    set_id: int,
    title: str = Form(""),
    description: str = Form(""),
    difficulty: str = Form("1"),
    test_input: list[str] | None = Form(default=None),
    test_expected: list[str] | None = Form(default=None),
    _: str = Depends(require_admin),
):
    personal = await get_set(set_id)
    if not personal:
        raise HTTPException(404, "Нет такого блока")
    test_input = _form_list(test_input)
    test_expected = _form_list(test_expected)
    clean_title = title.strip()
    clean_description = description.replace("\r\n", "\n").strip()
    tests = normalize_tests(test_input, test_expected)
    error = _task_error(clean_title, clean_description, tests)
    if error:
        body = (
            f"<p><a href='/personal/{set_id}'>← {html.escape(personal['title'])}</a></p>"
            + task_form(
                set_id,
                error=error,
                tests=tests or [{"input": "", "expected": ""}],
                title=clean_title,
                description=clean_description,
                difficulty=_difficulty(difficulty),
            )
        )
        return HTMLResponse(page("Новая задача", body), status_code=400)
    await create_personal_task(
        set_id, clean_title, clean_description, tests, _difficulty(difficulty)
    )
    return RedirectResponse(f"/personal/{set_id}?saved=1", status_code=303)


@router.get("/personal/{set_id}/task/{task_id}", response_class=HTMLResponse)
async def edit_task_form(set_id: int, task_id: int, _: str = Depends(require_admin)):
    personal, task = await _own_task(set_id, task_id)
    body = (
        f"<p><a href='/personal/{set_id}'>← {html.escape(personal['title'])}</a></p>"
        + task_form(set_id, task=task)
        + "<form method='post' action='/personal/"
        f"{set_id}/task/{task_id}/delete' onsubmit=\"return confirm('Удалить задачу?')\">"
        "<p><button type='submit' class='danger'>Удалить задачу</button></p>"
        "</form>"
    )
    return page(task["title"], body)


@router.post("/personal/{set_id}/task/{task_id}", response_class=HTMLResponse)
async def edit_task(
    set_id: int,
    task_id: int,
    title: str = Form(""),
    description: str = Form(""),
    difficulty: str = Form("1"),
    test_input: list[str] | None = Form(default=None),
    test_expected: list[str] | None = Form(default=None),
    _: str = Depends(require_admin),
):
    personal, task = await _own_task(set_id, task_id)
    test_input = _form_list(test_input)
    test_expected = _form_list(test_expected)
    clean_title = title.strip()
    clean_description = description.replace("\r\n", "\n").strip()
    tests = normalize_tests(test_input, test_expected)
    error = _task_error(clean_title, clean_description, tests)
    if error:
        task = {
            **task,
            "title": clean_title,
            "description": clean_description,
            "difficulty": _difficulty(difficulty),
            "tests": json.dumps(tests or [{"input": "", "expected": ""}], ensure_ascii=False),
        }
        body = (
            f"<p><a href='/personal/{set_id}'>← {html.escape(personal['title'])}</a></p>"
            + task_form(set_id, task=task, error=error)
        )
        return HTMLResponse(page("Править задачу", body), status_code=400)
    await update_personal_task(
        set_id,
        task_id,
        clean_title,
        clean_description,
        tests,
        _difficulty(difficulty),
    )
    return RedirectResponse(f"/personal/{set_id}?saved=1", status_code=303)


@router.post("/personal/{set_id}/task/{task_id}/delete")
async def remove_task(set_id: int, task_id: int, _: str = Depends(require_admin)):
    await _own_task(set_id, task_id)
    await delete_personal_task(set_id, task_id)
    return RedirectResponse(f"/personal/{set_id}", status_code=303)


def _task_error(title: str, description: str, tests: list[dict]) -> str:
    if not title:
        return "Напиши название."
    if not description:
        return "Напиши условие."
    if not tests:
        return "Нужен хотя бы один тест: что программа прочитает и что должна напечатать."
    return ""


async def _own_task(set_id: int, task_id: int):
    personal = await get_set(set_id)
    task = await get_task(task_id)
    if not personal or not task or task.get("set_id") != set_id:
        raise HTTPException(404, "Нет такой задачи")
    return personal, task
