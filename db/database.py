import aiosqlite


async def create_tables(app):
    conn = await aiosqlite.connect("stepik_killer.db")

    await conn.execute("PRAGMA foreign_keys = ON;")
    # пользователи
    await conn.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_tg INTEGER UNIQUE, 
        username TEXT NULL, 
        class INTEGER NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    # задачи
    await conn.execute("""CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 3),
        description TEXT NOT NULL,
        tests TEXT NOT NULL)""")

    # решения
    await conn.execute("""CREATE TABLE IF NOT EXISTS solutions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'new',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE)""")

    await conn.commit()
    await conn.close()
