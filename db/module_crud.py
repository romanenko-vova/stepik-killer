import aiosqlite


async def get_modules():
    async with aiosqlite.connect("stepik_killer.db") as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM modules")
        modules = await cur.fetchall()
        for i in range(len(modules)):
            modules[i] = dict(modules[i])
        return modules


async def add_module(title: str, description: str = None):
    async with aiosqlite.connect("stepik_killer.db") as conn:
        cursor = await conn.execute(
            """INSERT INTO modules(title, description)
                VALUES(?, ?)""",
            (title, description),
        )
        await conn.commit()
        return cursor.lastrowid
