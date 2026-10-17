import json

import aiosqlite

from config.config import DB_PATH
from db.seed import content_sig


def normalize_tests(inputs: list[str], expecteds: list[str]) -> list[dict]:
    # пустую пару пропускаем — это просто незаполненная строка формы
    tests = []
    count = max(len(inputs), len(expecteds))
    for i in range(count):
        raw_in = inputs[i] if i < len(inputs) else ""
        raw_out = expecteds[i] if i < len(expecteds) else ""
        inp = raw_in.replace("\r\n", "\n").strip()
        exp = raw_out.replace("\r\n", "\n").strip()
        if inp == "" and exp == "":
            continue
        tests.append({"input": inp, "expected": exp})
    return tests


async def sets_for_user(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """SELECT s.*
               FROM personal_sets s
               JOIN personal_set_access a ON a.set_id = s.id
               WHERE a.user_id = ?
               ORDER BY s.id""",
            (user_id,),
        )
        return [dict(row) for row in await cur.fetchall()]


async def all_sets() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """
            SELECT s.*,
                   u.first_name, u.username, u.id_tg,
                   (SELECT COUNT(*) FROM tasks t WHERE t.set_id = s.id) AS task_count
            FROM personal_sets s
            JOIN users u ON u.id = s.user_id
            ORDER BY s.id DESC
            """
        )
        return [dict(row) for row in await cur.fetchall()]


async def get_set(set_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM personal_sets WHERE id = ?", (set_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def grant_access(set_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO personal_set_access(set_id, user_id) VALUES(?, ?)",
            (set_id, user_id),
        )
        await conn.commit()


async def user_can_see_set(user_id: int, set_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "SELECT 1 FROM personal_set_access WHERE set_id = ? AND user_id = ?",
            (set_id, user_id),
        )
        return await cur.fetchone() is not None


async def find_set_by_title(user_id: int, title: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM personal_sets WHERE user_id = ? AND title = ?",
            (user_id, title),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def create_set(user_id: int, title: str) -> int:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "INSERT INTO personal_sets(user_id, title) VALUES(?, ?)",
            (user_id, title),
        )
        set_id = cur.lastrowid
        await conn.execute(
            "INSERT OR IGNORE INTO personal_set_access(set_id, user_id) VALUES(?, ?)",
            (set_id, user_id),
        )
        await conn.commit()
        return set_id


async def update_set_title(set_id: int, title: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE personal_sets SET title = ? WHERE id = ?",
            (title, set_id),
        )
        # в карточке решения тема берётся из tasks.topic
        await conn.execute(
            "UPDATE tasks SET topic = ? WHERE set_id = ?",
            (title, set_id),
        )
        await conn.commit()


async def delete_set(set_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """DELETE FROM solutions
               WHERE task_id IN (SELECT id FROM tasks WHERE set_id = ?)""",
            (set_id,),
        )
        await conn.execute("DELETE FROM tasks WHERE set_id = ?", (set_id,))
        await conn.execute(
            "DELETE FROM personal_set_access WHERE set_id = ?", (set_id,)
        )
        await conn.execute("DELETE FROM personal_sets WHERE id = ?", (set_id,))
        await conn.commit()


async def tasks_in_set(set_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM tasks WHERE set_id = ? ORDER BY id",
            (set_id,),
        )
        return [dict(row) for row in await cur.fetchall()]


async def tasks_with_status(set_id: int, user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """
            SELECT
                t.*,
                (
                    SELECT COUNT(*) FROM solutions s
                    WHERE s.user_id = ? AND s.task_id = t.id
                ) AS attempts,
                (
                    SELECT s.created_at FROM solutions s
                    WHERE s.user_id = ? AND s.task_id = t.id
                    ORDER BY s.id DESC LIMIT 1
                ) AS last_try,
                EXISTS(
                    SELECT 1 FROM solutions s
                    WHERE s.user_id = ? AND s.task_id = t.id
                      AND s.status = 'ok'
                      AND s.content_sig IS NOT NULL
                      AND s.content_sig = t.content_sig
                ) AS current_ok,
                EXISTS(
                    SELECT 1 FROM solutions s
                    WHERE s.user_id = ? AND s.task_id = t.id AND s.status = 'ok'
                ) AS ever_ok
            FROM tasks t
            WHERE t.set_id = ?
            ORDER BY t.id
            """,
            (user_id, user_id, user_id, user_id, set_id),
        )
        rows = [dict(row) for row in await cur.fetchall()]
        for row in rows:
            if row["current_ok"]:
                row["mark"] = "ok"
            elif row["ever_ok"]:
                row["mark"] = "stale"
            elif row["attempts"]:
                row["mark"] = "fail"
            else:
                row["mark"] = "none"
        return rows


async def personal_counts(user_id: int) -> tuple[int, int]:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            """SELECT COUNT(*)
               FROM tasks t
               JOIN personal_set_access a ON a.set_id = t.set_id
               WHERE a.user_id = ?""",
            (user_id,),
        )
        total = (await cur.fetchone())[0]
        cur = await conn.execute(
            """SELECT COUNT(DISTINCT t.id)
               FROM tasks t
               JOIN personal_set_access a ON a.set_id = t.set_id
               JOIN solutions sol ON sol.task_id = t.id
               WHERE a.user_id = ?
                 AND sol.user_id = ?
                 AND sol.status = 'ok'
                 AND sol.content_sig IS NOT NULL
                 AND sol.content_sig = t.content_sig""",
            (user_id, user_id),
        )
        solved = (await cur.fetchone())[0]
        return solved, total


async def user_can_open(user_id: int, task: dict | None) -> bool:
    if not task:
        return False
    # обычная задача курса — её видят все
    if not task.get("set_id"):
        return True
    return await user_can_see_set(user_id, task["set_id"])


def _tests_json(tests: list[dict]) -> str:
    return json.dumps(tests, ensure_ascii=False)


async def create_personal_task(
    set_id: int,
    title: str,
    description: str,
    tests: list[dict],
    difficulty: int,
) -> int:
    personal = await get_set(set_id)
    tests_json = _tests_json(tests)
    sig = content_sig(title, description, tests_json)
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            """INSERT INTO tasks(
                   title, topic, difficulty, description, tests, content_sig, set_id
               ) VALUES(?, ?, ?, ?, ?, ?, ?)""",
            (
                title,
                personal["title"],
                difficulty,
                description,
                tests_json,
                sig,
                set_id,
            ),
        )
        await conn.commit()
        return cur.lastrowid


async def update_personal_task(
    set_id: int,
    task_id: int,
    title: str,
    description: str,
    tests: list[dict],
    difficulty: int,
) -> bool:
    personal = await get_set(set_id)
    tests_json = _tests_json(tests)
    sig = content_sig(title, description, tests_json)
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            """UPDATE tasks
               SET title = ?, topic = ?, difficulty = ?, description = ?,
                   tests = ?, content_sig = ?
               WHERE id = ? AND set_id = ?""",
            (
                title,
                personal["title"],
                difficulty,
                description,
                tests_json,
                sig,
                task_id,
                set_id,
            ),
        )
        await conn.commit()
        return cur.rowcount > 0


async def delete_personal_task(set_id: int, task_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "SELECT id FROM tasks WHERE id = ? AND set_id = ?",
            (task_id, set_id),
        )
        if not await cur.fetchone():
            return False
        await conn.execute("DELETE FROM solutions WHERE task_id = ?", (task_id,))
        await conn.execute(
            "DELETE FROM tasks WHERE id = ? AND set_id = ?",
            (task_id, set_id),
        )
        await conn.commit()
        return True
