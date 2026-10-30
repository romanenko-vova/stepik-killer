"""
Собирает db/catalog.json из описаний тем (course/topics/*.py) и эталонных решений (course/solutions/<ключ>.py).

Как устроена задача в теме:
- examples: пары (ввод, ожидаемый вывод), написанные руками. Идут первыми — бот показывает
  первые 3 теста в условии. Эталон обязан на них совпасть, иначе сборка падает: так ловим ошибки
  в самих эталонах.
- hidden: только вводы. Ожидаемый вывод считает эталон.

Запуск из корня: python -m course.build_catalog
"""

import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOLUTIONS = ROOT / "course" / "solutions"
CATALOG = ROOT / "db" / "catalog.json"

MIN_TESTS = 7
MIN_HIDDEN = 4
SHOWN_IN_BOT = 3  # столько тестов бот печатает в условии

MODULES = [
    {
        "title": "Запуск",
        "description": "Ввод и вывод, числа, условия",
        "topics": ["t01_01", "t01_02"],
    },
    {
        "title": "Поток заказов",
        "description": "Циклы while и for",
        "topics": ["t02_01", "t02_02"],
    },
    {
        "title": "Меню и клиенты",
        "description": "Строки, списки, множества, словари",
        "topics": ["t03_01", "t03_02", "t03_03"],
    },
    {
        "title": "Автоматизация",
        "description": "Функции и итоговые задачи",
        "topics": ["t04_01", "t04_02"],
    },
]


def run_solution(key: str, stdin: str) -> str:
    """Так же, как песочница бота: python -I solution.py, сравнение после strip()."""
    path = SOLUTIONS / f"{key}.py"
    proc = subprocess.run(
        [sys.executable, "-I", path.name],
        input=stdin.encode("utf-8"),
        capture_output=True,
        timeout=5,
        cwd=SOLUTIONS,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{key}: эталон упал на вводе {stdin!r}:\n{proc.stderr.decode('utf-8', 'replace')}")
    return proc.stdout.decode("utf-8").strip()


def check_text(key: str, text: str):
    if "\xa0" in text:
        raise ValueError(f"{key}: неразрывный пробел в тексте")
    if "Романенко" in text:
        raise ValueError(f"{key}: старый бренд в тексте")


def build_task(key: str, spec: dict, number: int) -> dict:
    title = f"Задание {number}. {spec['title']}"
    description = spec["description"].strip()
    check_text(key, title + description)

    if not (SOLUTIONS / f"{key}.py").exists():
        raise FileNotFoundError(f"{key}: нет эталона course/solutions/{key}.py")

    tests = []
    for stdin, expected in spec["examples"]:
        check_text(key, stdin + expected)
        actual = run_solution(key, stdin)
        if actual != expected.strip():
            raise ValueError(
                f"{key}: эталон не совпал с примером.\nввод: {stdin!r}\nждали: {expected!r}\nполучили: {actual!r}"
            )
        tests.append({"input": stdin, "expected": expected.strip()})
    for stdin in spec["hidden"]:
        check_text(key, stdin)
        tests.append({"input": stdin, "expected": run_solution(key, stdin)})

    if len(tests) < MIN_TESTS:
        raise ValueError(f"{key}: тестов {len(tests)}, нужно не меньше {MIN_TESTS}")
    if len(tests) - SHOWN_IN_BOT < MIN_HIDDEN:
        raise ValueError(f"{key}: скрытых тестов {len(tests) - SHOWN_IN_BOT}, нужно не меньше {MIN_HIDDEN}")
    if len({json.dumps(t, ensure_ascii=False) for t in tests}) != len(tests):
        raise ValueError(f"{key}: есть одинаковые тесты")
    for t in tests:
        if t["expected"] == "":
            raise ValueError(f"{key}: пустой ожидаемый вывод на вводе {t['input']!r}")

    task = {"title": title, "difficulty": spec["difficulty"], "description": description, "tests": tests}
    if spec.get("image"):
        task["image"] = spec["image"]
    return task


def build() -> list:
    catalog = []
    seen_titles = set()
    for mi, module in enumerate(MODULES, 1):
        topics = []
        for ti, name in enumerate(module["topics"], 1):
            spec = importlib.import_module(f"course.topics.{name}").TOPIC
            assert spec["key"] == f"{mi:02d}-{ti:02d}", f"{name}: ключ темы {spec['key']} не на своём месте"
            tasks = []
            prev = 0
            for qi, task_spec in enumerate(spec["tasks"], 1):
                key = f"{spec['key']}-{qi:02d}"
                if not 1 <= task_spec["difficulty"] <= 5:
                    raise ValueError(f"{key}: сложность {task_spec['difficulty']} вне 1..5")
                if task_spec["difficulty"] < prev:
                    raise ValueError(f"{key}: сложность падает внутри темы")
                prev = task_spec["difficulty"]
                if task_spec["title"] in seen_titles:
                    raise ValueError(f"{key}: название «{task_spec['title']}» уже есть в курсе")
                seen_titles.add(task_spec["title"])
                tasks.append(build_task(key, task_spec, qi))
                print(f"  {key} ок, тестов {len(tasks[-1]['tests'])}")
            topics.append({"title": spec["title"], "tasks": tasks})
        catalog.append({"title": module["title"], "description": module["description"], "topics": topics})
    return catalog


def main():
    catalog = build()
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(t["tasks"]) for m in catalog for t in m["topics"])
    print(f"Записал {CATALOG}: модулей {len(catalog)}, задач {total}")


if __name__ == "__main__":
    main()
