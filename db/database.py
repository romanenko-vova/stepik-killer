import aiosqlite

from config.config import DB_PATH


async def create_tables(app):
    conn = await aiosqlite.connect(DB_PATH)

    # кто пользуется ботом и какой тон выбрал
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS users(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            id_tg INTEGER UNIQUE,
                            username TEXT NULL,
                            toxic_level INTEGER DEFAULT 0,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"""
    )

    await conn.execute(
        """CREATE TABLE IF NOT EXISTS modules(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            description TEXT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"""
    )
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS topics(
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                title TEXT NOT NULL,
                                description TEXT NULL,
                                module_id INTEGER,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"""
    )

    # topic — название темы, tests — json со списком тестов
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 3),
        description TEXT NOT NULL,
        tests TEXT NOT NULL,
        image TEXT)"""
    )

    # старые базы без колонки image — докидываем
    cur = await conn.execute("PRAGMA table_info(tasks)")
    cols = [row[1] for row in await cur.fetchall()]
    if "image" not in cols:
        await conn.execute("ALTER TABLE tasks ADD COLUMN image TEXT")

    await conn.execute(
        """CREATE TABLE IF NOT EXISTS catalog_meta(
                            id INTEGER PRIMARY KEY CHECK (id = 1),
                            sig TEXT NOT NULL)"""
    )

    await conn.execute(
        """CREATE TABLE IF NOT EXISTS solutions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'new',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE)"""
    )

    await conn.commit()
    await conn.close()

    # стартовый каталог кладём сразу при запуске бота
    from db.seed import seed_if_empty

    await seed_if_empty()
