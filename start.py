# start.py
import sqlite3
import os

DATABASE_PATH = 'database/messenger.db'

def init_db():
    # Создаем папку database, если её нет
    os.makedirs('database', exist_ok=True)
    
    # Подключаемся к БД
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    #Таблица с пользователями
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE NOT NULL,
            display_name TEXT,
            password_hash TEXT,
            is_tester BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    #Таблица для сообщении
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_uid TEXT NOT NULL,
            receiver_uid TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_group BOOLEAN DEFAULT FALSE
        )
    ''')
    
    #Таблица для "Избранных"
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS formyself (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_uid TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (message_id) REFERENCES messages (id)
        )
    ''')
    
    # Таблица зарезервированных UID для тестеров
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reserved_uids (
            uid TEXT PRIMARY KEY,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # Индексы для ускорения поиска
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_uid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_uid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_formyself_user ON formyself(user_uid)')
    
    #резервация UID для первых тестировщиков
    reserved_uids = ['007', '227', '774', '777', '123']
    for uid in reserved_uids:
        # Создаем "пустой" UID для тестеров
        cursor.execute('''
            INSERT OR IGNORE INTO users (uid, is_tester)
            VALUES (?, TRUE)
        ''', (uid,))
    
    conn.commit()
    conn.close()
    print("База данных инициализирована успешно!")
    print("Теперь, ты можешь запустить сам мессенджер")
    print("Запускай в следующий раз только в том случае, если удалил БД")

if __name__ == '__main__':
    init_db()