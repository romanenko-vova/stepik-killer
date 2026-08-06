"""
Наполняет БД демо-каталогом: 3 модуля → в каждом 3 темы → в каждой 3 задачи.
Запуск: python -m db.seed
"""

import asyncio
import json

from db.database import create_tables
from db.module_crud import add_module, get_modules
from db.topic_crud import add_topic
from db.zadacha_crud import add_task

# у всех задач одно и то же условие и один тест
DESCRIPTION = (
    "Считайте два целых числа (каждое на своей строке) "
    "и выведите их сумму.\n\n"
    "Пример:\n"
    "Ввод:\n2\n3\n"
    "Вывод:\n5"
)

TESTS = json.dumps(
    [{"input": "2\n3\n", "expected": "5"}],
    ensure_ascii=False,
)

# 3 модуля, у каждого 3 темы, у каждой темы 3 задачи (разные названия)
CATALOG = [
    {
        "title": "Основы Python",
        "topics": [
            {
                "title": "Ввод и вывод",
                "tasks": ["Сумма чисел", "Сложение", "Два числа"],
            },
            {
                "title": "Переменные",
                "tasks": ["Сложи и выведи", "Простая сумма", "Счёт"],
            },
            {
                "title": "Арифметика",
                "tasks": ["Плюс", "Сложение двух", "Итог суммы"],
            },
        ],
    },
    {
        "title": "Условия",
        "topics": [
            {
                "title": "if",
                "tasks": ["Сумма через if", "Условная сумма", "Если числа"],
            },
            {
                "title": "else",
                "tasks": ["Сумма с else", "Иначе сумма", "Ветка else"],
            },
            {
                "title": "elif",
                "tasks": ["Сумма с elif", "Несколько веток", "Цепочка elif"],
            },
        ],
    },
    {
        "title": "Циклы",
        "topics": [
            {
                "title": "for",
                "tasks": ["Сумма в for", "Цикл for", "Перебор for"],
            },
            {
                "title": "while",
                "tasks": ["Сумма в while", "Цикл while", "Пока while"],
            },
            {
                "title": "range",
                "tasks": ["Сумма и range", "Диапазон", "range и числа"],
            },
        ],
    },
]


async def create_demo_catalog():
    """Создаёт 3 модуля × 3 темы × 3 задачи. Если модули уже есть — ничего не делает."""
    await create_tables(None)

    if await get_modules():
        print("Модули уже есть, ничего не добавляю.")
        return

    for module in CATALOG:
        module_id = await add_module(module["title"])
        print(f"Модуль: {module['title']} (id={module_id})")

        for topic in module["topics"]:
            topic_id = await add_topic(topic["title"], module_id)
            print(f"  Тема: {topic['title']} (id={topic_id})")

            for task_title in topic["tasks"]:
                # topic в таблице tasks пока строка — кладём название темы
                task_id = await add_task(
                    task_title,
                    topic["title"],
                    1,
                    DESCRIPTION,
                    TESTS,
                )
                print(f"    Задача: {task_title} (id={task_id})")

    print("Готово: 3 модуля, 9 тем, 27 задач.")


if __name__ == "__main__":
    asyncio.run(create_demo_catalog())
