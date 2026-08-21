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


async def create_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT INTO users (id_tg) VALUES (?)", (user_id,))
        await conn.commit()
    return await get_user(user_id)


async def set_toxic_level(user_id: int, level: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET toxic_level = ? WHERE id_tg = ?",
            (level, user_id),
        )
        await conn.commit()
