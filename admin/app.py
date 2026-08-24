import asyncio
import html
import json
import logging
import re
import secrets

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config.config import ADMIN_HOST, ADMIN_PASSWORD, ADMIN_PORT, ADMIN_USER
from db.admin_crud import list_students, person_name, student_solutions, student_tasks
from db.users_crud import get_user_by_id
from db.zadacha_crud import get_task

security = HTTPBasic()
app = FastAPI(title="Stepik Killer admin")


def require_admin(creds: HTTPBasicCredentials = Depends(security)):
    user_ok = secrets.compare_digest(creds.username.encode(), ADMIN_USER.encode())
    pass_ok = secrets.compare_digest(
        creds.password.encode(), (ADMIN_PASSWORD or "").encode()
    )
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username


CSS = """
:root {
  --bg: #14110f;
  --paper: #1e1a16;
  --line: #3a322a;
  --ink: #f3e6d4;
  --muted: #a8947c;
  --ok: #7dba6a;
  --stale: #e0a14a;
  --fail: #d36c5a;
  --accent: #e7c27a;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  line-height: 1.45;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
header {
  padding: 22px 28px 10px;
  border-bottom: 1px solid var(--line);
}
header p { margin: 4px 0 0; color: var(--muted); font-size: 14px; }
main { padding: 22px 28px 60px; max-width: 1100px; }
table { width: 100%; border-collapse: collapse; }
th, td {
  text-align: left;
  padding: 10px 8px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}
th { color: var(--muted); font-weight: 500; font-size: 13px; letter-spacing: .04em; }
.mark { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.ok { color: var(--ok); }
.stale { color: var(--stale); }
.fail { color: var(--fail); }
.none { color: var(--muted); }
pre {
  background: #0e0c0a;
  border: 1px solid var(--line);
  padding: 14px;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  white-space: pre-wrap;
}
.card {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 16px 18px;
  margin: 16px 0;
}
.meta { color: var(--muted); font-size: 13px; }
h3 { font-size: 15px; margin: 16px 0 6px; font-weight: 600; }
.review {
  border-left: 3px solid var(--accent);
  padding: 8px 0 8px 14px;
  white-space: pre-wrap;
}
h1 { font-size: 28px; margin: 0; font-weight: 600; }
h2 { font-size: 20px; margin: 28px 0 8px; }
"""


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <h1><a href="/">Админка</a></h1>
    <p>Романенко Учит — прогресс и сданные решения</p>
  </header>
  <main>{body}</main>
</body>
</html>"""


def strip_tg_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def format_admin_tests(raw: str | None) -> str:
    if not raw:
        return "<p class='meta'>Отчёта тестов нет — попытка была до этой фичи.</p>"
    try:
        results = json.loads(raw)
    except json.JSONDecodeError:
        return f"<pre>{html.escape(raw)}</pre>"

    parts = []
    for item in results:
        n = item.get("n", "?")
        if item.get("ok"):
            parts.append(f"<p class='ok'>Тест {n}: прошёл</p>")
            continue
        if item.get("timeout"):
            parts.append(f"<p class='fail'>Тест {n}: слишком долго</p>")
            continue
        if item.get("error"):
            parts.append(
                f"<p class='fail'>Тест {n}: ошибка</p>"
                f"<pre>{html.escape(str(item['error']))}</pre>"
            )
            continue
        inp = str(item.get("input", "")).replace("\\n", "\n")
        exp = str(item.get("expected", "")).replace("\\n", "\n")
        got = str(item.get("actual", "")).replace("\\n", "\n")
        parts.append(
            f"<p class='fail'>Тест {n}: не прошёл</p>"
            "<pre>"
            f"Ввод:\n{html.escape(inp)}\n"
            f"Ожидалось:\n{html.escape(exp)}\n"
            f"Получено:\n{html.escape(got)}"
            "</pre>"
        )
    return "".join(parts) or "<p class='meta'>Пустой отчёт.</p>"


def mark_label(mark: str) -> str:
    return {
        "ok": '<span class="mark ok">✓ решена</span>',
        "stale": '<span class="mark stale">↻ изменилась</span>',
        "fail": '<span class="mark fail">✗ не прошла</span>',
        "none": '<span class="mark none">— нет попыток</span>',
    }.get(mark, mark)


@app.get("/", response_class=HTMLResponse)
async def index(_: str = Depends(require_admin)):
    students = await list_students()
    if not students:
        body = "<p>Пока никто не заходил в бота.</p>"
        return page("Ученики", body)

    rows = []
    for s in students:
        name = html.escape(s["name"])
        uname = f"@{html.escape(s['username'])}" if s.get("username") else "—"
        last = html.escape(str(s["last_try"] or "ещё не решал"))
        rows.append(
            "<tr>"
            f"<td><a href='/u/{s['id']}'>{name}</a></td>"
            f"<td>{uname}</td>"
            f"<td><code>{s['id_tg']}</code></td>"
            f"<td>{s['solved']} / {s['total']}</td>"
            f"<td>{s['stale'] or 0}</td>"
            f"<td>{s['attempts']}</td>"
            f"<td>{last}</td>"
            "</tr>"
        )
    body = (
        "<p class='meta'>Клик по имени — задачи и код. «Изменились» — решал старую версию, надо ещё раз.</p>"
        "<table><thead><tr>"
        "<th>Имя</th><th>Username</th><th>Telegram id</th>"
        "<th>Решено</th><th>Изменились</th><th>Попыток</th><th>Последняя</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return page("Ученики", body)


@app.get("/u/{user_pk}", response_class=HTMLResponse)
async def student(user_pk: int, _: str = Depends(require_admin)):
    user = await get_user_by_id(user_pk)
    if not user:
        raise HTTPException(404, "Нет такого ученика")
    tasks = await student_tasks(user_pk)
    rows = []
    for task in tasks:
        rows.append(
            "<tr>"
            f"<td>{html.escape(task['topic'])}</td>"
            f"<td><a href='/u/{user_pk}/task/{task['id']}'>{html.escape(task['title'])}</a></td>"
            f"<td>{mark_label(task['mark'])}</td>"
            f"<td>{task['attempts']}</td>"
            f"<td>{html.escape(str(task['last_try'] or '—'))}</td>"
            "</tr>"
        )
    name = html.escape(person_name(user))
    body = (
        f"<p><a href='/'>← все ученики</a></p>"
        f"<h2>{name}</h2>"
        f"<p class='meta'>tg {user['id_tg']}"
        f"{' · @' + html.escape(user['username']) if user.get('username') else ''}</p>"
        "<table><thead><tr><th>Тема</th><th>Задача</th><th>Статус</th><th>Попыток</th><th>Последняя</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return page(person_name(user), body)


@app.get("/u/{user_pk}/task/{task_id}", response_class=HTMLResponse)
async def solutions(user_pk: int, task_id: int, _: str = Depends(require_admin)):
    user = await get_user_by_id(user_pk)
    task = await get_task(task_id)
    if not user or not task:
        raise HTTPException(404, "Не найдено")
    items = await student_solutions(user_pk, task_id)
    cards = []
    if not items:
        cards.append("<p>Попыток ещё не было.</p>")
    for item in items:
        stale = item["status"] == "ok" and item["content_sig"] != item["task_sig"]
        status_html = "ok" if item["status"] == "ok" else item["status"]
        if stale:
            status_html = "ok · старая версия задачи"
        review = strip_tg_html(item["review"] or "")
        if review:
            review_html = f"<h3>Нейронка</h3><div class='review'>{html.escape(review)}</div>"
        else:
            review_html = "<h3>Нейронка</h3><p class='meta'>Ещё нет — либо старая попытка, либо ревью не успело записаться.</p>"
        cards.append(
            "<div class='card'>"
            f"<p class='meta'>#{item['id']} · {html.escape(str(item['created_at']))} · {html.escape(status_html)}</p>"
            f"<h3>Код</h3><pre>{html.escape(item['code'])}</pre>"
            f"<h3>Тесты</h3>{format_admin_tests(item.get('tests_json'))}"
            f"{review_html}"
            "</div>"
        )
    body = (
        f"<p><a href='/u/{user_pk}'>← {html.escape(person_name(user))}</a></p>"
        f"<h2>{html.escape(task['title'])}</h2>"
        f"<p class='meta'>{html.escape(task['topic'])}</p>"
        + "".join(cards)
    )
    return page(task["title"], body)


async def start_admin():
    if not ADMIN_PASSWORD:
        logging.warning("ADMIN_PASSWORD не задан — админка не стартует")
        return
    config = uvicorn.Config(
        app,
        host=ADMIN_HOST,
        port=ADMIN_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = False
    logging.info("Админка на http://%s:%s", ADMIN_HOST, ADMIN_PORT)
    asyncio.create_task(server.serve())
