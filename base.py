# base.py
import sqlite3
import bcrypt
import random
import string
from datetime import datetime, timedelta

DATABASE_PATH = 'database/messenger.db'

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени
        return conn
    
    # === Пользователи ===
    
    def register_tester_with_uid(self, uid, display_name, password):
        """Регистрация тестера по 3-значному UID"""
        user = self.get_user_by_uid(uid)
        if not user:
            return {'success': False, 'error': 'UID не существует'}
        
        if user['is_tester'] != 1:
            return {'success': False, 'error': 'Этот UID не для тестеров'}
        
        if user['display_name'] is not None:
            return {'success': False, 'error': 'Вы уже зарегистрировались, пожалуйста, используйте страницу авторизации для дальнейшего использования'}
        
        # Обновляем запись с никнеймом и паролем
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET display_name = ?, password_hash = ?
            WHERE uid = ?
        ''', (display_name, hashed, uid))
        conn.commit()
        conn.close()
        
        return {'success': True}

    def register_user(self, display_name, password):
        """Регистрация обычного пользователя с 5-значным UID"""
        uid = self.generate_uid_5digit()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (uid, display_name, password_hash, is_tester)
            VALUES (?, ?, ?, FALSE)
        ''', (uid, display_name, hashed))
        conn.commit()
        conn.close()
        
        return uid

    def verify_user_by_uid(self, uid, password):
        """Проверка UID и пароля"""
        user = self.get_user_by_uid(uid)
        if user and user['password_hash']:
            return bcrypt.checkpw(password.encode('utf-8'), user['password_hash'])
        return False

    def get_user_by_uid(self, uid):
        """Получение пользователя по UID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE uid = ?', (uid,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_display_name(self, display_name):
        """Получение данных пользователя по никнейму"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE display_name = ?', (display_name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def generate_uid_5digit(self):
        """Цикличная генерация 5-значного UID"""
        while True:
            uid = str(random.randint(10000, 99999))
            if not self.get_user_by_uid(uid):
                return uid

    def search_users_by_uid(self, uid_query):
        """Поиск пользователей по UID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT uid, display_name FROM users 
            WHERE uid LIKE ? AND display_name IS NOT NULL
            ORDER BY uid
            LIMIT 20
        ''', (f'%{uid_query}%',))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def search_users(self, query):
        """Поиск пользователей по никнейму"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT uid, display_name FROM users 
            WHERE display_name LIKE ? AND display_name IS NOT NULL
            ORDER BY display_name
            LIMIT 20
        ''', (f'%{query}%',))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_all_users(self):
        """Получение всех пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT uid, display_name FROM users WHERE display_name IS NOT NULL
        ''')
        rows = cursor.fetchall()
        conn.close()

        users = []
        for row in rows:
            users.append({
                'uid': row[0],
                'display_name': row[1]
            })
        return users
    
    # === Сообщения ===
    
    def add_message(self, sender_uid, receiver_uid, text, is_group=False):
        """Добавление нового сообщения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (sender_uid, receiver_uid, text, is_group)
            VALUES (?, ?, ?, ?)
        ''', (sender_uid, receiver_uid, text, is_group))
        conn.commit()
        conn.close()
    
    def get_private_messages(self, user1_uid, user2_uid):
        """Получение приватных сообщений между двумя пользователями"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sender_uid, receiver_uid, text, timestamp
            FROM messages 
            WHERE (
                (sender_uid = ? AND receiver_uid = ?) OR
                (sender_uid = ? AND receiver_uid = ?)
            )
            ORDER BY timestamp ASC
        ''', (user1_uid, user2_uid, user2_uid, user1_uid))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_group_messages(self, limit=50):
        """Получение сообщений из общего чата"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sender_uid, text, timestamp
            FROM messages 
            WHERE is_group = 1
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        # Возвращаем в обратном порядке (от старых к новым)
        messages = [dict(row) for row in reversed(rows)]
    
        # Добавляем display_name для каждого сообщения
        for msg in messages:
            user = self.get_user_by_uid(msg['sender_uid'])
            if user:
                msg['sender_display_name'] = user['display_name']
            else:
                msg['sender_display_name'] = msg['sender_uid']
        return messages

# Тестирование (можно удалить позже)
if __name__ == '__main__':
    db = Database()
    print("Database module loaded successfully!")