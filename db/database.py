import aiosqlite


async def create_tables(app):
    conn = await aiosqlite.connect("lead.db")
    
    # Таблица пользователей
    await conn.execute("""CREATE TABLE IF NOT EXISTS users(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            id_tg INTEGER UNIQUE, 
                            username TEXT NULL, 
                            class INTEGER NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    
    await conn.execute("""CREATE TABLE IF NOT EXISTS modules(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            description TEXT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")

    # Таблица викторин
    await conn.execute("""CREATE TABLE IF NOT EXISTS victorins(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            topic TEXT, 
                            class INTEGER,
                            module_id INTEGER NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE SET NULL)""")
    
    # Таблица вопросов
    await conn.execute("""CREATE TABLE IF NOT EXISTS questions(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT, 
                        vict_id INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (vict_id) REFERENCES victorins(id) ON DELETE CASCADE)""")

    # Таблица ответов
    await conn.execute("""CREATE TABLE IF NOT EXISTS answers(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT, 
                        quest_id INTEGER,
                        correct INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (quest_id) REFERENCES questions(id) ON DELETE CASCADE)""")   
    
    await conn.commit()
    await conn.close()