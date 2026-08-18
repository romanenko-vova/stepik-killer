import aiosqlite

from config.config import DB_PATH


async def get_topics_by_module_id(module_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM topics WHERE module_id = ?", (module_id,)
        )
        topics = await cur.fetchall()
        for i in range(len(topics)):
            topics[i] = dict(topics[i])
        return topics


async def get_topic(topic_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        topic = await cur.fetchone()
        if topic is None:
            return None
        return dict(topic)


async def add_topic(title: str, module_id: int, description: str = None):
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            """INSERT INTO topics(title, description, module_id)
                VALUES(?, ?, ?)""",
            (title, description, module_id),
        )
        await conn.commit()
        return cursor.lastrowid
