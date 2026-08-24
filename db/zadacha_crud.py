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
    # только те, что закрыты на ТЕКУЩЕЙ версии условия
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            """SELECT DISTINCT s.task_id
               FROM solutions s
               JOIN tasks t ON t.id = s.task_id
               WHERE s.user_id = ?
                 AND s.status = 'ok'
                 AND s.content_sig IS NOT NULL
                 AND s.content_sig = t.content_sig""",
            (user_id,),
        )
        rows = await cur.fetchall()
        return {row[0] for row in rows}


async def get_stale_task_ids(user_id: int) -> set[int]:
    # когда-то решил, но задача с тех пор поменялась
    solved = await get_solved_task_ids(user_id)
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            """SELECT DISTINCT s.task_id
               FROM solutions s
               JOIN tasks t ON t.id = s.task_id
               WHERE s.user_id = ?
                 AND s.status = 'ok'
                 AND (
                   s.content_sig IS NULL
                   OR s.content_sig != t.content_sig
                 )""",
            (user_id,),
        )
        rows = await cur.fetchall()
        return {row[0] for row in rows} - solved


async def get_progress(user_id: int) -> tuple[int, int, int]:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT COUNT(*) FROM tasks")
        total = (await cur.fetchone())[0]
    solved = len(await get_solved_task_ids(user_id))
    stale = len(await get_stale_task_ids(user_id))
    return solved, total, stale


async def add_solution(user_id: int, task_id: int, code: str, status: str = "new"):
    task = await get_task(task_id)
    sig = task.get("content_sig") if task else None
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            """INSERT INTO solutions(user_id, task_id, code, status, content_sig)
                VALUES(?, ?, ?, ?, ?)""",
            (user_id, task_id, code, status, sig),
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
