import aiosqlite

from config.config import DB_PATH


async def get_modules():
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM modules")
        modules = await cur.fetchall()
        for i in range(len(modules)):
            modules[i] = dict(modules[i])
        return modules


async def get_module(module_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM modules WHERE id = ?", (module_id,))
        module = await cur.fetchone()
        if module is None:
            return None
        return dict(module)


async def add_module(title: str, description: str = None):
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            """INSERT INTO modules(title, description)
                VALUES(?, ?)""",
            (title, description),
        )
        await conn.commit()
        return cursor.lastrowid
