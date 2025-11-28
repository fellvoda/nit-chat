# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from base import Database
import os
import random
import string
import bcrypt
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

db = Database()

# === Вспомогательные функции ===

def require_login(f):
    """Декоратор для проверки авторизации"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_login' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# === Маршруты ===

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/tester-register', methods=['GET', 'POST'])
def tester_register():
    """Регистрация тестера по UID"""
    if request.method == 'POST':
        uid = request.form['uid']
        display_name = request.form['display_name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return render_template('tester_register.html', error='Пароли не совпадают')
        
        if len(password) < 6:
            return render_template('tester_register.html', error='Пароль должен быть не менее 6 символов')
        
        result = db.register_tester_with_uid(uid, display_name, password)
        if result['success']:
            return redirect(url_for('login'))
        else:
            if 'уже зарегистрировались' in result['error']:
                return render_template('tester_register.html', error=result['error'])
            return render_template('tester_register.html', error=result['error'])
    
    return render_template('tester_register.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Обычная регистрация (автоматический UID)"""
    if request.method == 'POST':
        display_name = request.form['display_name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return render_template('register.html', error='Пароли не совпадают')
        
        if len(password) < 6:
            return render_template('register.html', error='Пароль должен быть не менее 6 символов')
        
        uid = db.register_user(display_name, password)
        return render_template('register_success.html', uid=uid)
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход по UID"""
    if request.method == 'POST':
        uid = request.form['uid']
        password = request.form['password']
        
        if db.verify_user_by_uid(uid, password):
            user = db.get_user_by_uid(uid)
            session['user_login'] = user['uid']
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error='Неверный UID или пароль')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход"""
    session.pop('user_login', None)
    return redirect(url_for('index'))

@app.route('/chat')
@require_login
def chat():
    """Общий чат"""
    user = db.get_user_by_uid(session['user_login'])
    return render_template('chat.html', user=user)

@app.route('/pm/<username>')
@require_login
def private_messages(username):
    """Личные сообщения"""
    current_user = db.get_user_by_uid(session['user_login'])
    
    if username == 'formyself':
        # Для "Избранного" используем текущего пользователя как "псевдо-получателя"
        target_user = {
            'uid': 'formyself',
            'display_name': 'formyself'
        }
    else:
        # Для обычных пользователей ищем по UID
        target_user = db.get_user_by_uid(username)
    
    if not target_user:
        return "Пользователь не найден", 404
    
    return render_template('pm.html', 
                         current_user=current_user, 
                         target_user=target_user)

# === API маршруты ===

@app.route('/api/ping')
@require_login
def api_ping():
    """Пинг для поддержания сессии"""
    return jsonify({'status': 'ok'})

@app.route('/api/users/search')
@require_login
def api_search_users():
    """Поиск пользователей по UID или никнейму"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    # Поиск по UID
    users_by_uid = db.search_users_by_uid(query)
    # Поиск по никнейму
    users_by_name = db.search_users(query)
    
    # Объединяем и убираем дубликаты
    all_users = users_by_uid + users_by_name
    unique_users = []
    seen_uids = set()
    
    for user in all_users:
        if user['uid'] not in seen_uids:
            unique_users.append(user)
            seen_uids.add(user['uid'])
    
    return jsonify(unique_users)

@app.route('/api/messages/group')
@require_login
def api_group_messages():
    """Получение сообщений из общего чата"""
    messages = db.get_group_messages()
    return jsonify(messages)

@app.route('/api/messages/private/<username>')
@require_login
def api_private_messages(username):
    """Получение приватных сообщений"""
    current_user = db.get_user_by_uid(session['user_login'])
    
    if username == 'formyself':
        # Для "Избранного" используем текущего пользователя
        target_user = current_user
    else:
        target_user = db.get_user_by_uid(username)
    
    if not target_user:
        return jsonify({'error': 'User not found'}), 404
    
    messages = db.get_private_messages(current_user['uid'], target_user['uid'])
    
    # Добавляем display_name к каждому сообщению
    for msg in messages:
        sender = db.get_user_by_uid(msg['sender_uid'])
        if sender:
            msg['sender_display_name'] = sender['display_name']
        else:
            msg['sender_display_name'] = msg['sender_uid']
    
    return jsonify(messages)

@app.route('/api/messages/send', methods=['POST'])
@require_login
def api_send_message():
    """Отправка сообщения"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        receiver_param = data.get('receiver', '')
        is_group = data.get('is_group', False)
        
        if not text:
            return jsonify({'error': 'Message text is required'}), 400
        
        sender = db.get_user_by_uid(session['user_login'])
        
        if is_group:
            # Отправка в общий чат
            db.add_message(sender['uid'], 'group', text, is_group=True)
        elif receiver_param == 'formyself':
            # Отправка в избранное (сообщение самому себе)
            db.add_message(sender['uid'], sender['uid'], text)
        else:
            # Отправка в приват
            receiver = db.get_user_by_uid(receiver_param)
            if not receiver:
                return jsonify({'error': 'Receiver not found'}), 404
            db.add_message(sender['uid'], receiver['uid'], text)
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Ошибка в api_send_message: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/chats/list')
@require_login
def api_chats_list():
    """Получение списка чатов"""
    current_user = db.get_user_by_uid(session['user_login'])
    if not current_user:
        return jsonify([]), 401
    
    # Получаем всех пользователей
    users = db.get_all_users()
    
    chats = []
    
    # Добавляем "Избранное" как первый чат после общего
    chats.append({
        'username': 'formyself',      # UID для ссылки
        'display_name': 'Избранное', # Отображаемое имя
        'is_favorite': True
    })
    
    # Для каждого пользователя проверяем, есть ли переписка
    for user in users:
        if user['uid'] != current_user['uid']:
            # Получаем сообщения между пользователями
            messages = db.get_private_messages(current_user['uid'], user['uid'])
            
            if len(messages) > 0:  # Если есть сообщения
                chats.append({
                    'username': user['uid'],          # UID для ссылки
                    'display_name': user['display_name']  # Отображаемое имя
                })
    
    # "Избранное" всегда первое после общего чата
    result_chats = [chats[0]] + chats[1:]
    
    return jsonify(result_chats)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)