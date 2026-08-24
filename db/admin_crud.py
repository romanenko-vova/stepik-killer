import aiosqlite

from config.config import DB_PATH


def person_name(user: dict) -> str:
    if user.get("first_name"):
        return user["first_name"]
    if user.get("username"):
        return "@" + user["username"]
    return f"id {user['id_tg']}"


async def list_students() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT COUNT(*) FROM tasks")
        total = (await cur.fetchone())[0]
        cur = await conn.execute(
            """
            SELECT
                u.id,
                u.id_tg,
                u.username,
                u.first_name,
                u.created_at,
                (
                    SELECT COUNT(DISTINCT s.task_id)
                    FROM solutions s
                    JOIN tasks t ON t.id = s.task_id
                    WHERE s.user_id = u.id
                      AND s.status = 'ok'
                      AND s.content_sig IS NOT NULL
                      AND s.content_sig = t.content_sig
                ) AS solved,
                (
                    SELECT COUNT(DISTINCT s.task_id)
                    FROM solutions s
                    JOIN tasks t ON t.id = s.task_id
                    WHERE s.user_id = u.id
                      AND s.status = 'ok'
                      AND (
                        s.content_sig IS NULL
                        OR s.content_sig != t.content_sig
                      )
                      AND s.task_id NOT IN (
                        SELECT s2.task_id
                        FROM solutions s2
                        JOIN tasks t2 ON t2.id = s2.task_id
                        WHERE s2.user_id = u.id
                          AND s2.status = 'ok'
                          AND s2.content_sig IS NOT NULL
                          AND s2.content_sig = t2.content_sig
                      )
                ) AS stale,
                (SELECT COUNT(*) FROM solutions WHERE user_id = u.id) AS attempts,
                (SELECT MAX(created_at) FROM solutions WHERE user_id = u.id) AS last_try
            FROM users u
            ORDER BY (last_try IS NULL), last_try DESC
            """
        )
        rows = [dict(r) for r in await cur.fetchall()]
        for row in rows:
            row["total"] = total
            row["name"] = person_name(row)
        return rows


async def student_tasks(user_pk: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """
            SELECT
                t.id,
                t.title,
                t.topic,
                t.content_sig,
                (
                    SELECT s.status
                    FROM solutions s
                    WHERE s.user_id = ? AND s.task_id = t.id
                    ORDER BY s.id DESC
                    LIMIT 1
                ) AS last_status,
                (
                    SELECT s.created_at
                    FROM solutions s
                    WHERE s.user_id = ? AND s.task_id = t.id
                    ORDER BY s.id DESC
                    LIMIT 1
                ) AS last_try,
                (
                    SELECT COUNT(*)
                    FROM solutions s
                    WHERE s.user_id = ? AND s.task_id = t.id
                ) AS attempts,
                EXISTS(
                    SELECT 1 FROM solutions s
                    WHERE s.user_id = ? AND s.task_id = t.id
                      AND s.status = 'ok'
                      AND s.content_sig IS NOT NULL
                      AND s.content_sig = t.content_sig
                ) AS current_ok,
                EXISTS(
                    SELECT 1 FROM solutions s
                    WHERE s.user_id = ? AND s.task_id = t.id
                      AND s.status = 'ok'
                ) AS ever_ok
            FROM tasks t
            ORDER BY t.id
            """,
            (user_pk, user_pk, user_pk, user_pk, user_pk),
        )
        rows = [dict(r) for r in await cur.fetchall()]
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


async def student_solutions(user_pk: int, task_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """
            SELECT s.id, s.code, s.status, s.content_sig, s.created_at,
                   s.tests_json, s.review, t.content_sig AS task_sig
            FROM solutions s
            JOIN tasks t ON t.id = s.task_id
            WHERE s.user_id = ? AND s.task_id = ?
            ORDER BY s.id DESC
            """,
            (user_pk, task_id),
        )
        return [dict(r) for r in await cur.fetchall()]
