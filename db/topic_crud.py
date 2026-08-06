import aiosqlite


async def get_topics_by_module_id(module_id):
    async with aiosqlite.connect("stepik_killer.db") as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM topics WHERE module_id = ?", (module_id,)
        )
        topics = await cur.fetchall()
        for i in range(len(topics)):
            topics[i] = dict(topics[i])
        return topics


async def add_topic(title: str, module_id: int, description: str = None):
    async with aiosqlite.connect("stepik_killer.db") as conn:
        cursor = await conn.execute(
            """INSERT INTO topics(title, description, module_id)
                VALUES(?, ?, ?)""",
            (title, description, module_id),
        )
        await conn.commit()
        return cursor.lastrowid
