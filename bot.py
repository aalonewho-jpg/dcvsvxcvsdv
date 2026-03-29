import json
import sqlite3
import random
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
import requests

# Конфигурация
BOT_TOKEN = "8523906756:AAGmlRufvfhz_4lGHbOWEvhqfOzJr0LbGcE"
ADMIN_CHAT_ID = "-1003620844942"  # ID канала или админа
OWNER_USERNAME = "@enclox"  # Для звезд

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# --- База данных ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (telegram_id INTEGER PRIMARY KEY,
                  nickname TEXT UNIQUE,
                  game_id TEXT,
                  registered_at TEXT,
                  avatar TEXT DEFAULT 'default',
                  banner TEXT DEFAULT 'default',
                  theme TEXT DEFAULT 'white',
                  coins INTEGER DEFAULT 0)''')
    # Таблица статистики
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats
                 (telegram_id INTEGER PRIMARY KEY,
                  elo INTEGER DEFAULT 100,
                  kills INTEGER DEFAULT 0,
                  deaths INTEGER DEFAULT 0,
                  assists INTEGER DEFAULT 0,
                  matches INTEGER DEFAULT 0,
                  wins INTEGER DEFAULT 0,
                  avg REAL DEFAULT 0.0,
                  kd REAL DEFAULT 0.0,
                  wr REAL DEFAULT 0.0)''')
    # Таблица инвентаря
    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  telegram_id INTEGER,
                  item_type TEXT,
                  item_id TEXT,
                  item_name TEXT,
                  item_icon TEXT,
                  is_new INTEGER DEFAULT 1)''')
    conn.commit()
    conn.close()

init_db()

# --- Хелперы ---
def get_level_by_elo(elo):
    if elo < 200: return 1
    elif elo < 500: return 2
    elif elo < 820: return 3
    elif elo < 1000: return 4
    elif elo < 1350: return 5
    elif elo < 1600: return 6
    elif elo < 1880: return 7
    elif elo < 2000: return 8
    elif elo < 2400: return 9
    else: return 10

def update_stats(telegram_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT kills, deaths, matches, wins FROM user_stats WHERE telegram_id = ?', (telegram_id,))
    stats = c.fetchone()
    if stats:
        kills, deaths, matches, wins = stats
        avg = round(kills / matches, 2) if matches > 0 else 0
        kd = round(kills / deaths, 2) if deaths > 0 else 0
        wr = round((wins / matches) * 100, 1) if matches > 0 else 0
        c.execute('UPDATE user_stats SET avg = ?, kd = ?, wr = ? WHERE telegram_id = ?', (avg, kd, wr, telegram_id))
        conn.commit()
    conn.close()

# --- API Эндпоинты ---
@app.route('/')
def index():
    return render_template_string(open('index.html', encoding='utf-8').read())

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    telegram_id = data.get('telegram_id')
    nickname = data.get('nickname')
    game_id = data.get('game_id')
    
    if not telegram_id or not nickname or not game_id:
        return jsonify({'success': False, 'error': 'Missing data'})
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Проверка существует ли
    c.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    if c.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'Already registered'})
    
    # Проверка ника
    c.execute('SELECT * FROM users WHERE nickname = ?', (nickname,))
    if c.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'Nickname taken'})
    
    # Регистрация
    c.execute('INSERT INTO users (telegram_id, nickname, game_id, registered_at, coins) VALUES (?, ?, ?, ?, ?)',
              (telegram_id, nickname, game_id, datetime.now().isoformat(), 100)) # Стартовые 100 монет
    c.execute('INSERT INTO user_stats (telegram_id) VALUES (?)', (telegram_id,))
    conn.commit()
    conn.close()
    
    # Отправка админу
    try:
        requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json={
            'chat_id': ADMIN_CHAT_ID,
            'text': f'🆕 Новый игрок!\nНик: {nickname}\nID: {game_id}\nTG ID: {telegram_id}'
        })
    except: pass
    
    return jsonify({'success': True})

@app.route('/api/profile/<int:telegram_id>')
def get_profile(telegram_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT nickname, game_id, registered_at, avatar, banner, theme, coins FROM users WHERE telegram_id = ?', (telegram_id,))
    user = c.fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    c.execute('SELECT elo, kills, deaths, assists, matches, wins, avg, kd, wr FROM user_stats WHERE telegram_id = ?', (telegram_id,))
    stats = c.fetchone()
    conn.close()
    
    level = get_level_by_elo(stats[0]) if stats else 1
    return jsonify({
        'nickname': user[0], 'game_id': user[1], 'registered_at': user[2],
        'avatar': user[3], 'banner': user[4], 'theme': user[5], 'coins': user[6],
        'elo': stats[0], 'kills': stats[1], 'deaths': stats[2], 'assists': stats[3],
        'matches': stats[4], 'wins': stats[5], 'avg': stats[6], 'kd': stats[7],
        'wr': stats[8], 'level': level
    })

@app.route('/api/inventory/<int:telegram_id>')
def get_inventory(telegram_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT item_type, item_id, item_name, item_icon, is_new FROM inventory WHERE telegram_id = ?', (telegram_id,))
    items = [{'type': row[0], 'id': row[1], 'name': row[2], 'icon': row[3], 'is_new': bool(row[4])} for row in c.fetchall()]
    conn.close()
    return jsonify(items)

@app.route('/api/buy_case', methods=['POST'])
def buy_case():
    data = request.json
    telegram_id = data.get('telegram_id')
    case_name = data.get('case_name')
    case_price = data.get('case_price')
    case_icon = data.get('case_icon')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT coins FROM users WHERE telegram_id = ?', (telegram_id,))
    coins = c.fetchone()[0]
    
    if coins < case_price:
        conn.close()
        return jsonify({'success': False, 'error': 'Not enough coins'})
    
    # Списываем монеты
    c.execute('UPDATE users SET coins = coins - ? WHERE telegram_id = ?', (case_price, telegram_id))
    # Добавляем кейс в инвентарь
    c.execute('INSERT INTO inventory (telegram_id, item_type, item_id, item_name, item_icon, is_new) VALUES (?, ?, ?, ?, ?, ?)',
              (telegram_id, 'case', case_name.lower().replace(' ', '_'), case_name, case_icon, 1))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/open_case', methods=['POST'])
def open_case():
    data = request.json
    telegram_id = data.get('telegram_id')
    case_id = data.get('case_id')
    
    # Симуляция выпадения (пример для "loser_check" выпадает Sakura)
    # В реальном проекте тут сложная логика с шансами
    if 'loser_check' in case_id.lower():
        reward = {'type': 'banner', 'id': 'sakura', 'name': 'Sakura', 'icon': 'SakuraEvent.jpg'}
    elif 'a_rush' in case_id.lower():
        reward = {'type': 'banner', 'id': 'hellin_frozen', 'name': 'Hellin Frozen', 'icon': 'hellinfrozen.jpg'}
    else:
        reward = {'type': 'theme', 'id': 'dark', 'name': 'Темная тема', 'icon': 'theme_dark.png'}
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Удаляем кейс из инвентаря
    c.execute('DELETE FROM inventory WHERE telegram_id = ? AND item_id = ? AND item_type = "case" LIMIT 1', (telegram_id, case_id))
    # Добавляем предмет
    c.execute('INSERT INTO inventory (telegram_id, item_type, item_id, item_name, item_icon, is_new) VALUES (?, ?, ?, ?, ?, ?)',
              (telegram_id, reward['type'], reward['id'], reward['name'], reward['icon'], 1))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'reward': reward})

@app.route('/api/apply_item', methods=['POST'])
def apply_item():
    data = request.json
    telegram_id = data.get('telegram_id')
    item_type = data.get('item_type')
    item_id = data.get('item_id')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if item_type == 'avatar':
        c.execute('UPDATE users SET avatar = ? WHERE telegram_id = ?', (item_id, telegram_id))
    elif item_type == 'banner':
        c.execute('UPDATE users SET banner = ? WHERE telegram_id = ?', (item_id, telegram_id))
    elif item_type == 'theme':
        c.execute('UPDATE users SET theme = ? WHERE telegram_id = ?', (item_id, telegram_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/mark_seen', methods=['POST'])
def mark_seen():
    data = request.json
    telegram_id = data.get('telegram_id')
    item_id = data.get('item_id')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE inventory SET is_new = 0 WHERE telegram_id = ? AND item_id = ?', (telegram_id, item_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/complete_task', methods=['POST'])
def complete_task():
    telegram_id = request.json.get('telegram_id')
    # Выдаем кейс Loser Check
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO inventory (telegram_id, item_type, item_id, item_name, item_icon, is_new) VALUES (?, ?, ?, ?, ?, ?)',
              (telegram_id, 'case', 'loser_check', 'Loser Check', 'LoserCheck.jpg', 1))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/create_stars_invoice', methods=['POST'])
def create_stars_invoice():
    data = request.json
    telegram_id = data.get('telegram_id')
    stars_amount = data.get('stars')
    coins_amount = stars_amount * 40  # 1 звезда = 40 монет
    
    # Создаем инвойс в Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
    payload = {
        "title": f"Пополнение {coins_amount} Coins",
        "description": f"Покупка {coins_amount} Test Coins за {stars_amount} Telegram Stars",
        "payload": f"coins_{telegram_id}_{stars_amount}",
        "provider_token": "",  # Для звезд оставляем пустым
        "currency": "XTR",
        "prices": [{"label": f"{stars_amount} Stars", "amount": stars_amount}]
    }
    response = requests.post(url, json=payload).json()
    if response.get('ok'):
        return jsonify({'success': True, 'url': response['result']})
    return jsonify({'success': False, 'error': 'Invoice failed'})

# Webhook для успешной оплаты (Telegram пришлет сюда)
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.json
    if 'pre_checkout_query' in update:
        query = update['pre_checkout_query']
        answer = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/answerPreCheckoutQuery', json={
            'pre_checkout_query_id': query['id'],
            'ok': True
        })
    elif 'message' in update and 'successful_payment' in update['message']:
        payload = update['message']['successful_payment']['invoice_payload']
        stars_amount = int(payload.split('_')[2])
        telegram_id = int(payload.split('_')[1])
        coins_amount = stars_amount * 40
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('UPDATE users SET coins = coins + ? WHERE telegram_id = ?', (coins_amount, telegram_id))
        conn.commit()
        conn.close()
        
        requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json={
            'chat_id': telegram_id,
            'text': f'✅ Пополнение успешно! +{coins_amount} Test Coins.'
        })
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
