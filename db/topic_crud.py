import aiosqlite

async def get_topics_by_module_id(module_id):
    async with aiosqlite.connect("stepik_killer.db") as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM topic WHERE module_id = ?", (module_id,))
        topics = await cur.fetchall()
        for i in range(len(topics)):
            topics[i] = dict(topics[i])
        return topics