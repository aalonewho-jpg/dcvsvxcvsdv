import os
import sqlite3
import json
import random
import string
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, PreCheckoutQuery, LabeledPrice
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
from aiohttp.web import Request, Response

# ---------------------------- CONFIG ----------------------------
class Config:
    BOT_TOKEN = "8281884357:AAH9ABK98yyPcdRDef91Lpqgf8ov5QgNn7o"
    ADMIN_GROUP_ID = -1003620844942   # канал админа @alonewho
    PROJECT_NAME = "Test Faceit Leo"
    ADMIN_IDS = [7545275828]  # замени на свой Telegram ID, если нужно

    # Параметры ELO (как в оригинале)
    ELO_BASE_WIN = 10
    ELO_BASE_LOSS = -10
    ELO_PER_KILL = 1
    ELO_PER_HELP = 0.5
    ELO_PER_DEATH = -0.5
    MIN_ELO = 0

    # Максимум участников команды (не используется пока, но пусть будет)
    MAX_TEAM_MEMBERS = 2

    # Список кейсов (для магазина)
    CASES = {
        "Loser Check": {"price": 75, "icon": "LoserCheck.webp", "items": ["Banner Sakura"]},
        "Faceit Open": {"price": 100, "icon": "FaceitOpen.webp", "items": ["Banner Faceit", "Ramka Faceit"]},
        "Alonewho CS2": {"price": 250, "icon": "AlonewhoCS2.webp", "items": ["Theme Discord", "Banner Alonewho"]},
        "Free Leo": {"price": 120, "icon": "FreeLeo.webp", "items": ["Theme Leo", "Banner Leo"]},
        "Delete Game": {"price": 80, "icon": "DeleteGame.webp", "items": ["Banner Delete", "Ramka Delete"]},
        "B Rush": {"price": 50, "icon": "BRush.webp", "items": ["Banner Hellin Frozen"]},
        "A Rush": {"price": 50, "icon": "ARush.webp", "items": ["Banner Hellin Frozen"]},
        "Sakura Event": {"price": 400, "icon": "SakuraEvent.png", "items": ["Banner Sakura", "Theme Sakura", "Ramka Sakura"]}
    }

    # Все возможные предметы с их типами (для инвентаря)
    ITEMS = {
        "Banner Sakura": {"type": "banner", "icon": "SakuraEvent.jpg"},
        "Banner Hellin Frozen": {"type": "banner", "icon": "hellinfrozen.jpg"},
        "Banner Faceit": {"type": "banner", "icon": "FaceitOpen.png"},
        "Banner Alonewho": {"type": "banner", "icon": "AlonewhoCS2.png"},
        "Banner Leo": {"type": "banner", "icon": "FreeLeo.png"},
        "Banner Delete": {"type": "banner", "icon": "DeleteGame.png"},
        "Ramka Faceit": {"type": "frame", "icon": "frame_faceit.png"},
        "Ramka Delete": {"type": "frame", "icon": "frame_delete.png"},
        "Ramka Sakura": {"type": "frame", "icon": "frame_sakura.png"},
        "Theme Discord": {"type": "theme", "icon": "theme_discord.png"},
        "Theme Leo": {"type": "theme", "icon": "theme_leo.png"},
        "Theme Sakura": {"type": "theme", "icon": "theme_sakura.png"},
    }

# ---------------------------- DATABASE ----------------------------
class Database:
    def __init__(self, db_name="panic_faceit.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                game_nickname TEXT UNIQUE,
                game_id TEXT UNIQUE,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                coins INTEGER DEFAULT 0,
                stats_kills INTEGER DEFAULT 0,
                stats_helps INTEGER DEFAULT 0,
                stats_deaths INTEGER DEFAULT 0,
                matches INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                elo INTEGER DEFAULT 100,
                current_banner TEXT DEFAULT 'default_banner.jpg',
                current_avatar TEXT DEFAULT 'default_avatar.png',
                current_theme TEXT DEFAULT 'light'
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                item_type TEXT,
                is_new INTEGER DEFAULT 1,
                obtained_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, item_name)
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                user_id INTEGER PRIMARY KEY,
                profile_viewed INTEGER DEFAULT 0
            )''')
            conn.commit()

    def user_exists(self, user_id: int) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            return c.fetchone() is not None

    def register_user(self, user_id: int, username: str, nickname: str, game_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (user_id, username, game_nickname, game_id) VALUES (?,?,?,?)",
                          (user_id, username, nickname, game_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_user(self, user_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_user_by_nickname(self, nickname: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE game_nickname = ?", (nickname,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_user_by_game_id(self, game_id: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE game_id = ?", (game_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def add_coins(self, user_id: int, amount: int):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
            conn.commit()

    def spend_coins(self, user_id: int, amount: int) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
            coins = c.fetchone()[0]
            if coins >= amount:
                c.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (amount, user_id))
                conn.commit()
                return True
            return False

    def add_item(self, user_id: int, item_name: str, item_type: str):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO inventory (user_id, item_name, item_type, is_new) VALUES (?,?,?,1)",
                      (user_id, item_name, item_type))
            conn.commit()

    def get_inventory(self, user_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT item_name, item_type, is_new FROM inventory WHERE user_id = ? ORDER BY obtained_at DESC", (user_id,))
            rows = c.fetchall()
            return [dict(r) for r in rows]

    def mark_item_seen(self, user_id: int, item_name: str):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("UPDATE inventory SET is_new = 0 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            conn.commit()

    def update_stats(self, user_id: int, kills: int, helps: int, deaths: int, win: bool):
        # Обновление ELO и статистики (для админ-команды /reg, здесь заглушка)
        pass  # Для мини-приложения статистика пока статична, но метод оставлен для совместимости

    def get_task(self, user_id: int) -> Dict:
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT profile_viewed FROM tasks WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row:
                return {"profile_viewed": row[0]}
            else:
                c.execute("INSERT INTO tasks (user_id, profile_viewed) VALUES (?,0)", (user_id,))
                conn.commit()
                return {"profile_viewed": 0}

    def complete_task(self, user_id: int, task_name: str):
        if task_name == "view_profile":
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                c.execute("UPDATE tasks SET profile_viewed = 1 WHERE user_id = ?", (user_id,))
                conn.commit()
                # Награда: кейс "Loser Check"
                self.add_item(user_id, "Case Loser Check", "case")
                self.add_coins(user_id, 10)  # бонус

    def apply_item(self, user_id: int, item_name: str, item_type: str):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            if item_type == "banner":
                c.execute("UPDATE users SET current_banner = ? WHERE user_id = ?", (item_name, user_id))
            elif item_type == "avatar":
                c.execute("UPDATE users SET current_avatar = ? WHERE user_id = ?", (item_name, user_id))
            elif item_type == "theme":
                c.execute("UPDATE users SET current_theme = ? WHERE user_id = ?", (item_name, user_id))
            conn.commit()

    def open_case(self, user_id: int, case_name: str) -> str:
        # Симуляция открытия кейса: выпадение случайного предмета из списка кейса
        case_data = Config.CASES.get(case_name.replace("Case ", ""), None)
        if not case_data:
            return None
        possible_items = case_data["items"]
        if not possible_items:
            return None
        won_item = random.choice(possible_items)
        item_info = Config.ITEMS.get(won_item, {"type": "banner", "icon": "default.png"})
        self.add_item(user_id, won_item, item_info["type"])
        return won_item

    def get_profile_stats(self, user_id: int) -> Dict:
        user = self.get_user(user_id)
        if not user:
            return {}
        kills = user.get("stats_kills", 0)
        deaths = user.get("stats_deaths", 1)
        helps = user.get("stats_helps", 0)
        matches = user.get("matches", 0)
        wins = user.get("wins", 0)
        kd = round(kills / deaths, 2) if deaths > 0 else 0.0
        avg = round(kills / matches, 2) if matches > 0 else 0.0
        wr = round((wins / matches) * 100, 1) if matches > 0 else 0.0
        elo = user.get("elo", 100)
        level = 1
        if elo >= 200: level = 2
        if elo >= 500: level = 3
        if elo >= 820: level = 4
        if elo >= 1000: level = 5
        if elo >= 1350: level = 6
        if elo >= 1600: level = 7
        if elo >= 1880: level = 8
        if elo >= 2000: level = 9
        if elo >= 2400: level = 10
        return {
            "nickname": user["game_nickname"],
            "game_id": user["game_id"],
            "elo": elo,
            "level": level,
            "kd": kd,
            "avg": avg,
            "kills": kills,
            "assists": helps,
            "deaths": deaths,
            "matches": matches,
            "wins": wins,
            "losses": matches - wins,
            "wr": wr,
            "registered_at": user["registered_at"],
            "coins": user["coins"],
            "current_banner": user.get("current_banner", "default_banner.jpg"),
            "current_avatar": user.get("current_avatar", "default_avatar.png"),
            "current_theme": user.get("current_theme", "light")
        }

db = Database()

# ---------------------------- BOT + WEB SERVER ----------------------------
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()

# Состояния для регистрации (через WebApp не нужны, но оставим на всякий)
class RegState(StatesGroup):
    waiting = State()

# --- Команда /start ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if db.user_exists(user_id):
        # Отправляем WebApp
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🎮 Открыть Test Faceit Leo", web_app=WebAppInfo(url="https://ваш-домен:8080")))
        await message.answer("Добро пожаловать обратно! Нажми кнопку, чтобы открыть мини-приложение.", reply_markup=keyboard.as_markup())
    else:
        # Отправляем WebApp с регистрацией
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="📝 Зарегистрироваться", web_app=WebAppInfo(url="https://ваш-домен:8080")))
        await message.answer("Привет! Нажми кнопку и пройди регистрацию в нашем мини-приложении.", reply_markup=keyboard.as_markup())

# --- Обработка данных из WebApp (через POST) ---
async def handle_webapp(request: Request):
    data = await request.json()
    action = data.get("action")
    user_id = data.get("user_id")
    if not user_id:
        return Response(text="No user_id", status=400)

    if action == "register":
        nickname = data.get("nickname")
        game_id = data.get("game_id")
        username = data.get("username", "")
        if db.get_user_by_nickname(nickname) or db.get_user_by_game_id(game_id):
            return Response(text="Nickname or Game ID already taken", status=400)
        success = db.register_user(user_id, username, nickname, game_id)
        if success:
            # Выдаём начальный кейс за регистрацию (опционально)
            db.add_item(user_id, "Case Loser Check", "case")
            db.add_coins(user_id, 50)
            return Response(text="OK")
        else:
            return Response(text="Registration failed", status=400)

    elif action == "get_profile":
        stats = db.get_profile_stats(user_id)
        return Response(text=json.dumps(stats), content_type="application/json")

    elif action == "get_inventory":
        inv = db.get_inventory(user_id)
        return Response(text=json.dumps(inv), content_type="application/json")

    elif action == "mark_seen":
        item_name = data.get("item_name")
        db.mark_item_seen(user_id, item_name)
        return Response(text="OK")

    elif action == "open_case":
        case_name = data.get("case_name")
        # Проверяем, есть ли такой кейс в инвентаре
        inv = db.get_inventory(user_id)
        case_item = next((i for i in inv if i["item_name"] == case_name and i["item_type"] == "case"), None)
        if not case_item:
            return Response(text="No such case", status=400)
        # Удаляем кейс из инвентаря
        with sqlite3.connect(db.db_name) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, case_name))
            conn.commit()
        # Открываем
        won = db.open_case(user_id, case_name)
        if won:
            return Response(text=json.dumps({"won": won}), content_type="application/json")
        else:
            return Response(text="Case empty", status=400)

    elif action == "buy_case":
        case_name = data.get("case_name")
        case_data = Config.CASES.get(case_name)
        if not case_data:
            return Response(text="Case not found", status=400)
        price = case_data["price"]
        if db.spend_coins(user_id, price):
            db.add_item(user_id, f"Case {case_name}", "case")
            return Response(text="OK")
        else:
            return Response(text="Not enough coins", status=400)

    elif action == "complete_task":
        task = data.get("task")
        if task == "view_profile":
            task_status = db.get_task(user_id)
            if not task_status["profile_viewed"]:
                db.complete_task(user_id, "view_profile")
                return Response(text="Task completed, case added")
            else:
                return Response(text="Already completed")
        return Response(text="Unknown task", status=400)

    elif action == "apply_item":
        item_name = data.get("item_name")
        item_type = data.get("item_type")
        db.apply_item(user_id, item_name, item_type)
        return Response(text="OK")

    elif action == "get_task":
        task = db.get_task(user_id)
        return Response(text=json.dumps(task), content_type="application/json")

    elif action == "get_cases_shop":
        # Возвращаем список кейсов с ценами и иконками
        shop = [{"name": name, "price": info["price"], "icon": info["icon"]} for name, info in Config.CASES.items()]
        return Response(text=json.dumps(shop), content_type="application/json")

    return Response(text="Unknown action", status=400)

# --- Платежи через Telegram Stars (простая заглушка) ---
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout: PreCheckoutQuery):
    await pre_checkout.answer(ok=True)

@dp.message(Command("buy_stars"))
async def buy_stars(message: Message):
    prices = [LabeledPrice(label="1000 Test Coins", amount=2500)]  # 25 Stars = 2500 копеек
    await bot.send_invoice(
        message.chat.id,
        title="Пополнение Test Coins",
        description="Покупка 1000 Test Coins",
        payload="coins_1000",
        provider_token="",  # для Stars можно оставить пустым
        currency="XTR",
        prices=prices,
        start_parameter="test_coins"
    )

@dp.message(Command("admin_stats"))
async def admin_stats(message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
    # простая статистика
    await message.answer("Admin panel placeholder")

# --- Запуск веб-сервера ---
async def start_web():
    app = web.Application()
    app.router.add_post("/webapp", handle_webapp)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logging.info("Web server started on port 8080")

async def main():
    logging.basicConfig(level=logging.INFO)
    await start_web()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())