"""
Набор попыток под рилсы: нарочно написанные ошибки, понятные зрителю без знания Python.

    python -m scripts.reel_set [--prod prod_copy/stepik_killer_prod.db] [--runs 3] [--out REEL_SET.md]

Каждая попытка проходит песочницу (честный отчёт тестов), потом --runs раз бот с текущим
промптом и моделью из настроек. Серия «5 попыток одного ученика» прогоняется цепочкой:
бот видит свои прошлые ответы, как в жизни. Лучший ответ отмечается руками в готовом файле.
"""

import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from handlers.gpt_handlers import format_tests_plain  # noqa: E402
from services import verify_python_code as prompt  # noqa: E402
from services.code_runner import run_tests  # noqa: E402

CATALOG = json.loads((ROOT / "db" / "catalog.json").read_text(encoding="utf-8"))
TASKS = {
    f"{mi:02d}-{ti:02d}-{qi:02d}": task
    for mi, module in enumerate(CATALOG, 1)
    for ti, topic in enumerate(module["topics"], 1)
    for qi, task in enumerate(topic["tasks"], 1)
}

# задачи «сложи два числа» в каталоге нет, а ошибка 2 + 3 = 23 — самая понятная зрителю
SUM_TASK = {
    "title": "Сложи два числа (не из каталога)",
    "description": "Считай два целых числа, каждое с новой строки, и выведи их сумму.",
    "tests": [
        {"input": "2\n3", "expected": "5"},
        {"input": "10\n7", "expected": "17"},
        {"input": "0\n0", "expected": "0"},
        {"input": "-4\n4", "expected": "0"},
    ],
}

CASES = [
    ("Строки вместо чисел: 2 + 3 = 23", SUM_TASK, "a = input()\nb = input()\nprint(a + b)"),
    (
        "= вместо == в if",
        "01-01-03",
        "vova = int(input())\nanya = int(input())\nif vova = anya:\n    print('Ничья')\n"
        "elif vova < anya:\n    print('Вова быстрее')\nelse:\n    print('Аня быстрее')",
    ),
    (
        "Хардкод под пример из условия",
        "01-02-01",
        "n = int(input())\nif n == 230:\n    print('ДА')\nelse:\n    print('НЕТ')",
    ),
    (
        "print внутри цикла вместо одного ответа",
        "02-01-03",
        "s = 0\nx = int(input())\nwhile x != 0:\n    s = s + x\n    print(s)\n    x = int(input())",
    ),
    (
        "Бесконечный while",
        "02-01-01",
        "n = int(input())\ni = 1\nwhile i <= n:\n    print(i)",
    ),
    (
        "Список на миллиард",
        "02-02-01",
        "n = int(input())\nnums = [0] * 10**9\nfor i in range(n):\n    print(i)",
    ),
    (
        "ChatGPT-стиль на задачу в две строки (тесты проходят)",
        "01-01-01",
        'def main():\n    """\n    Читает имя клиента и выводит приветствие.\n\n    Returns:\n'
        '        None\n    """\n    try:\n        name = input().strip()\n'
        '        greeting = f"Привет, {name}! Твой заказ принят."\n        print(greeting)\n'
        '    except Exception as e:\n        print(f"Произошла ошибка: {e}")\n\n\n'
        'if __name__ == "__main__":\n    main()',
    ),
    (
        "Как в школьном учебнике: три if, a и b, print с запятыми (тесты проходят)",
        "01-01-03",
        "a = int(input())\nb = int(input())\nif a < b:\n    print('Вова', 'быстрее')\n"
        "if a > b:\n    print('Аня', 'быстрее')\nif a == b:\n    print('Ничья')",
    ),
    ("Код из одной строки", "01-01-04", "n = int(input())"),
]


def series_from_prod(db_path: str) -> tuple[dict, list[str]]:
    """Реальная серия «Сумма до нуля» с прода: попытки 3–7 — четыре провала и верное решение."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    user_id, task_id = conn.execute(
        """SELECT s.user_id, s.task_id FROM solutions s JOIN tasks t ON t.id = s.task_id
           WHERE t.title = 'Задание 3. Сумма до нуля'
           GROUP BY 1, 2 ORDER BY COUNT(*) DESC LIMIT 1"""
    ).fetchone()
    title, description, tests = conn.execute(
        "SELECT title, description, tests FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    codes = [
        row[0]
        for row in conn.execute(
            "SELECT code FROM solutions WHERE user_id = ? AND task_id = ? ORDER BY id", (user_id, task_id)
        )
    ]
    conn.close()
    task = {"title": f"{title} (старый каталог)", "description": description, "tests": json.loads(tests)}
    return task, codes[2:7]


def one_line(text: str) -> str:
    # задача одной строкой: первое предложение условия
    first = " ".join(text.split())
    for stop in (". ", "! "):
        if stop in first:
            return first.split(stop)[0] + "."
    return first


def answer_lines(answer: str) -> list[str]:
    return ["> " + line for line in prompt.strip_html(answer).splitlines()] or ["> (пусто)"]


async def check(task: dict, code: str) -> tuple[bool, str]:
    ok, results = await run_tests(code, task["tests"])
    return ok, format_tests_plain(results)


async def single(name: str, task: dict, code: str, runs: int) -> list[str]:
    ok, report = await check(task, code)
    answers = await asyncio.gather(
        *[
            prompt.review_solution(code, task["description"], report, 3, 1, [{"code": code, "status": "fail"}], ok)
            for _ in range(runs)
        ]
    )
    status = "✅ тесты прошли" if ok else "❌ тесты не прошли"
    lines = [
        f"## {name}",
        "",
        f"**Задача:** {task['title']} — {one_line(task['description'])} <sub>{status}</sub>",
        "",
        "```python",
        code,
        "```",
        "",
    ]
    for i, answer in enumerate(answers, 1):
        lines += [f"**Ответ {i}**", "", *answer_lines(answer), ""]
    print(f"готово: {name}", flush=True)
    return lines


async def series(task: dict, codes: list[str], runs: int) -> list[str]:
    checked = [await check(task, code) for code in codes]

    async def chain():
        history, out = [], []
        for n, (code, (ok, report)) in enumerate(zip(codes, checked), 1):
            history = (history + [{"code": code, "status": "ok" if ok else "fail"}])[-3:]
            answer = await prompt.review_solution(code, task["description"], report, 3, n, history, ok)
            history[-1]["review"] = answer
            out.append(answer)
        return out

    chains = await asyncio.gather(*[chain() for _ in range(runs)])
    lines = [
        "## 5 попыток одного ученика (реальная серия с прода, без имён)",
        "",
        f"**Задача:** {task['title']} — {one_line(task['description'])}",
        "",
        "Каждый прогон — отдельная цепочка: бот видит свои прошлые ответы в этой серии.",
        "",
    ]
    for n, (code, (ok, _)) in enumerate(zip(codes, checked), 1):
        status = "✅ тесты прошли" if ok else "❌ тесты не прошли"
        lines += [f"### Попытка {n} <sub>{status}</sub>", "", "```python", code, "```", ""]
        for i, answers in enumerate(chains, 1):
            lines += [f"**Ответ {i}**", "", *answer_lines(answers[n - 1]), ""]
    print("готово: серия", flush=True)
    return lines


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prod", default=str(ROOT / "prod_copy" / "stepik_killer_prod.db"))
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", default=str(ROOT / "REEL_SET.md"))
    args = parser.parse_args()

    lines = [
        "# Попытки под рилсы",
        "",
        f"Режим «Без пощады», модель `{prompt.GPT_MODEL}`, текущий промпт. "
        f"Каждая попытка прогнана через бота {args.runs} раза, ⭐ — лучший ответ.",
        "Критерий: первая строка смешна человеку, который никогда не писал код.",
        "",
    ]
    for name, task_ref, code in CASES:
        task = TASKS[task_ref] if isinstance(task_ref, str) else task_ref
        lines += await single(name, task, code, args.runs)
    task, codes = series_from_prod(args.prod)
    lines += await series(task, codes, args.runs)
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Готово:", args.out)


if __name__ == "__main__":
    asyncio.run(main())
