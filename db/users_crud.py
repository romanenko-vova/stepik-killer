import aiosqlite

from config.config import DB_PATH


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM users WHERE id_tg = ?", (user_id,))
        user = await cur.fetchone()
        if user is None:
            return None
        return dict(user)


async def get_user_by_id(pk: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM users WHERE id = ?", (pk,))
        user = await cur.fetchone()
        if user is None:
            return None
        return dict(user)


async def create_user(user_id: int, username: str | None = None, first_name: str | None = None):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO users (id_tg, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name),
        )
        await conn.commit()
    return await get_user(user_id)


async def touch_user(user_id: int, username: str | None = None, first_name: str | None = None):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET username = ?, first_name = ? WHERE id_tg = ?",
            (username, first_name, user_id),
        )
        await conn.commit()
    return await get_user(user_id)


async def set_toxic_level(user_id: int, level: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET toxic_level = ? WHERE id_tg = ?",
            (level, user_id),
        )
        await conn.commit()
