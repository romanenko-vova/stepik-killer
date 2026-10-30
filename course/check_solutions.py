"""
Прогоняет эталоны course/solutions/<ключ>.py против db/catalog.json и пишет course/REPORT.md.
Проверка та же, что в песочнице бота: python -I solution.py, вывод и ожидание сравниваются после strip().

Запуск из корня: python -m course.check_solutions
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOLUTIONS = ROOT / "course" / "solutions"
CATALOG = ROOT / "db" / "catalog.json"
REPORT = ROOT / "course" / "REPORT.md"
SHOWN_IN_BOT = 3


def run(key: str, stdin: str) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-I", f"{key}.py"],
        input=stdin.encode("utf-8"),
        capture_output=True,
        timeout=5,
        cwd=SOLUTIONS,
    )
    if proc.returncode != 0:
        return False, proc.stderr.decode("utf-8", "replace")[-300:]
    return True, proc.stdout.decode("utf-8").strip()


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows = []
    problems = []
    total_tests = 0
    for mi, module in enumerate(catalog, 1):
        for ti, topic in enumerate(module["topics"], 1):
            for qi, task in enumerate(topic["tasks"], 1):
                key = f"{mi:02d}-{ti:02d}-{qi:02d}"
                tests = task["tests"]
                passed = 0
                for n, test in enumerate(tests, 1):
                    ok, out = run(key, test["input"])
                    if ok and out == test["expected"].strip():
                        passed += 1
                    else:
                        problems.append(f"{key} тест {n}: ввод {test['input']!r}, ждали {test['expected']!r}, получили {out!r}")
                total_tests += len(tests)
                hidden = len(tests) - SHOWN_IN_BOT
                mark = "✅" if passed == len(tests) else "❌"
                rows.append(
                    f"| {key} | {task['title']} | {task['difficulty']} | {len(tests)} | {hidden} | {passed}/{len(tests)} {mark} |"
                )

    tasks_total = len(rows)
    lines = [
        "# Прогон эталонов против тестов каталога",
        "",
        f"Дата: {date.today().isoformat()}. Команда: `python -m course.check_solutions`.",
        f"Задач: {tasks_total}, тестов: {total_tests}, упало: {len(problems)}.",
        "",
        "Скрытых — это тесты, которых ученик не видит: бот печатает первые 3.",
        "",
        "| Ключ | Задача | Сл. | Тестов | Скрытых | Эталон |",
        "|---|---|---|---|---|---|",
        *rows,
    ]
    if problems:
        lines += ["", "## Падения", ""] + [f"- {p}" for p in problems]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Задач {tasks_total}, тестов {total_tests}, упало {len(problems)}. Отчёт: {REPORT}")
    for p in problems:
        print(" ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
