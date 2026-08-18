import aiosqlite

from config.config import DB_PATH


async def add_task(
    title: str,
    topic: str,
    difficulty: int,
    description: str,
    tests_json: str,
    image: str | None = None,
):
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            """INSERT INTO tasks(title, topic, difficulty, description, tests, image)
                VALUES(?, ?, ?, ?, ?, ?)""",
            (title, topic, difficulty, description, tests_json, image),
        )
        await conn.commit()
        return cursor.lastrowid


async def get_task(task_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = await cur.fetchone()
        if task is None:
            return None
        return dict(task)


async def get_tasks_by_topic(topic_title: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM tasks WHERE topic = ? ORDER BY id", (topic_title,)
        )
        tasks = await cur.fetchall()
        for i in range(len(tasks)):
            tasks[i] = dict(tasks[i])
        return tasks


async def get_solved_task_ids(user_id: int) -> set[int]:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            """SELECT DISTINCT task_id
               FROM solutions
               WHERE user_id = ? AND status = 'ok'""",
            (user_id,),
        )
        rows = await cur.fetchall()
        return {row[0] for row in rows}


async def add_solution(user_id: int, task_id: int, code: str, status: str = "new"):
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            """INSERT INTO solutions(user_id, task_id, code, status)
                VALUES(?, ?, ?, ?)""",
            (user_id, task_id, code, status),
        )
        await conn.commit()
        return cursor.lastrowid


async def get_attempt_count(user_id: int, task_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM solutions WHERE user_id = ? AND task_id = ?",
            (user_id, task_id),
        )
        result = await cur.fetchone()
        return result[0]


async def get_recent_attempts(user_id: int, task_id: int, limit: int = 3):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """SELECT code, status, created_at
               FROM solutions
               WHERE user_id = ? AND task_id = ?
               ORDER BY id DESC
               LIMIT ?""",
            (user_id, task_id, limit),
        )
        attempts = await cur.fetchall()
        return [dict(attempt) for attempt in reversed(attempts)]
