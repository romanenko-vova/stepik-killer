"""
Стартовый каталог: 1 модуль, 2 темы, по 3 задачи.
Кладётся сам при запуске бота. Вручную: python -m db.seed
"""

import asyncio
import json

import aiosqlite

from config.config import DB_PATH
from db.module_crud import add_module, get_modules
from db.topic_crud import add_topic
from db.zadacha_crud import add_task

CATALOG = [
    {
        "title": "Базовый Python",
        "description": "Переменные и условия",
        "topics": [
            {
                "title": "Работа с переменными",
                "tasks": [
                    {
                        "title": "Сумма двух чисел",
                        "difficulty": 1,
                        "description": (
                            "Даны два целых числа, каждое с новой строки.\n"
                            "Выведите их сумму."
                        ),
                        "tests": [
                            {"input": "2\n3\n", "expected": "5"},
                            {"input": "10\n-4\n", "expected": "6"},
                            {"input": "0\n0\n", "expected": "0"},
                        ],
                    },
                    {
                        "title": "Периметр прямоугольника",
                        "difficulty": 1,
                        "description": (
                            "Даны длина и ширина прямоугольника, каждое число с новой строки.\n"
                            "Выведите периметр: 2 * (длина + ширина)."
                        ),
                        "tests": [
                            {"input": "2\n3\n", "expected": "10"},
                            {"input": "5\n5\n", "expected": "20"},
                            {"input": "1\n8\n", "expected": "18"},
                        ],
                    },
                    {
                        "title": "Числа наоборот",
                        "difficulty": 1,
                        "description": (
                            "Даны два числа a и b, каждое с новой строки.\n"
                            "Выведите сначала b, потом a. Каждое число с новой строки."
                        ),
                        "tests": [
                            {"input": "1\n2\n", "expected": "2\n1"},
                            {"input": "10\n20\n", "expected": "20\n10"},
                            {"input": "-3\n7\n", "expected": "7\n-3"},
                        ],
                    },
                ],
            },
            {
                "title": "Условия",
                "tasks": [
                    {
                        "title": "Знак числа",
                        "difficulty": 1,
                        "description": (
                            "Дано одно целое число.\n"
                            "Если оно больше нуля — выведите слово положительное.\n"
                            "Если меньше нуля — отрицательное.\n"
                            "Если равно нулю — ноль.\n"
                            "Слово выводите маленькими буквами, как написано."
                        ),
                        "tests": [
                            {"input": "5\n", "expected": "положительное"},
                            {"input": "-2\n", "expected": "отрицательное"},
                            {"input": "0\n", "expected": "ноль"},
                        ],
                    },
                    {
                        "title": "Большее из двух",
                        "difficulty": 1,
                        "description": (
                            "Даны два целых числа, каждое с новой строки.\n"
                            "Выведите большее из них.\n"
                            "Если числа равны — выведите любое."
                        ),
                        "tests": [
                            {"input": "3\n7\n", "expected": "7"},
                            {"input": "10\n2\n", "expected": "10"},
                            {"input": "4\n4\n", "expected": "4"},
                        ],
                    },
                    {
                        "title": "Чёт или нечёт",
                        "difficulty": 1,
                        "description": (
                            "Дано одно целое число.\n"
                            "Если оно делится на 2 без остатка — выведите чёт.\n"
                            "Иначе выведите нечёт.\n"
                            "Точно так, маленькими буквами."
                        ),
                        "tests": [
                            {"input": "4\n", "expected": "чёт"},
                            {"input": "7\n", "expected": "нечёт"},
                            {"input": "0\n", "expected": "чёт"},
                        ],
                    },
                ],
            },
        ],
    },
]


async def clear_catalog():
    # юзеров не трогаем, каталог пересобираем
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM solutions")
        await conn.execute("DELETE FROM tasks")
        await conn.execute("DELETE FROM topics")
        await conn.execute("DELETE FROM modules")
        await conn.commit()


async def seed_if_empty():
    modules = await get_modules()
    if len(modules) == 1 and modules[0]["title"] == "Базовый Python":
        return

    await clear_catalog()

    for module in CATALOG:
        module_id = await add_module(module["title"], module["description"])
        for topic in module["topics"]:
            await add_topic(topic["title"], module_id)
            for task in topic["tasks"]:
                await add_task(
                    task["title"],
                    topic["title"],
                    task["difficulty"],
                    task["description"],
                    json.dumps(task["tests"], ensure_ascii=False),
                )


if __name__ == "__main__":
    from db.database import create_tables

    asyncio.run(create_tables(None))
