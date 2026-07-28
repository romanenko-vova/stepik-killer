import aiosqlite


async def add_task(
    title: str, topic: str, difficulty: int, description: str, tests_json: str
):
    async with aiosqlite.connect("stepik_killer.db") as conn:
        cursor = await conn.execute(
            """INSERT INTO tasks(title, topic, difficulty, description, tests)
                VALUES(?, ?, ?, ?, ?)""",
            (title, topic, difficulty, description, tests_json),
        )
        await conn.commit()
        return cursor.lastrowid


async def add_solution(user_id: int, task_id: int, code: str):
    async with aiosqlite.connect("stepik_killer.db") as conn:
        cursor = await conn.execute(
            """INSERT INTO solutions(user_id, task_id, code)
                VALUES(?, ?, ?)""",
            (user_id, task_id, code),
        )
        await conn.commit()
        return cursor.lastrowid
