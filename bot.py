import asyncio
import os
import json
import random
import string
from datetime import datetime, timedelta
import re
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, LabeledPrice,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand
)
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не установлен в переменных окружения")

PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")  # Для оплаты Stars

# 👑 АДМИНЫ
ADMIN_IDS = [123456789]  # Замените на ваш ID
ADMIN_USERNAMES = ["Durove14"]  # Замените на ваш username

ACCESS_LINK = "https://t.me/+s1xuxYDZbzxjNWZi"  # Исправьте на корректный URL

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_FILE = "users.json"
PRICE_STARS = 75
PENDING_TIMEOUT_HOURS = 24  # Время ожидания подтверждения оплаты в часах

# ---------- БАЗА ДАННЫХ ----------
@asynccontextmanager
async def get_users():
    """Контекстный менеджер для безопасной работы с базой данных"""
    try:
        if not os.path.exists(DB_FILE):
            data = {}
        else:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        yield data
    except Exception as e:
        logger.error(f"Ошибка загрузки базы данных: {e}")
        yield {}
    finally:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения базы данных: {e}")

async def load_users():
    async with get_users() as users:
        return users

async def save_users(data):
    async with get_users() as _:
        pass  # Сохранение происходит автоматически при выходе из контекста

def generate_key():
    """Генерация уникального ключа доступа"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

def valid_code(code):
    """Проверка формата кода (12 символов, буквы и цифры)"""
    return bool(re.fullmatch(r"[A-Za-z0-9]{12}", code))

async def is_unique_private_id(code):
    """Проверка уникальности private_id"""
    users = await load_users()
    for user_data in users.values():
        if user_data.get('private_id') == code:
            return False
    return True

# ---------- АДМИН ----------
def is_admin(user):
    """Проверка прав администратора"""
    return (user.id in ADMIN_IDS) or (user.username in ADMIN_USERNAMES)

# ---------- UI ----------
def main_menu():
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить ЗБТ", callback_data="buy")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])

def buy_menu():
    """Меню оплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Stars", callback_data="stars")],
        [InlineKeyboardButton(text="💳 Donation", url="https://dalink.to/bountygames3")],
        [InlineKeyboardButton(text="📸 Я оплатил", callback_data="proof")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

def admin_approval_menu(user_id):
    """Клавиатура для модерации"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ok_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"no_{user_id}")
        ]
    ])

# ---------- КОМАНДЫ ----------
async def set_commands():
    """Установка команд бота"""
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск"),
        BotCommand(command="private", description="Регистрация ID"),
        BotCommand(command="unprivate", description="Удалить ID (админ)")
    ])

# ---------- СТАРТ ----------
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎮 <b>OxideRevival</b>\n\n"
        "🔥 Закрытый Бета Тест\n"
        "💰 75⭐ или 100₽\n\n"
        "👇 Выбери действие:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# ---------- PRIVATE ----------
@dp.message(Command("private"))
async def private_cmd(message: Message):
    uid = str(message.from_user.id)
    args = message.text.split()

    async with get_users() as users:
        # Показать текущий статус если нет аргументов
        if uid in users and "private_id" in users[uid] and len(args) == 1:
            data = users[uid]
            await message.answer(
                f"🆔 ID: {data.get('private_id')}\n"
                f"📅 Дата: {data.get('time_reg')}\n"
                f"💎 Статус: {data.get('status', '-')}\n"
                f"🔑 Ключ: {data.get('key', 'нет')}"
            )
            return

        if len(args) != 2:
            await message.answer("❌ Используйте: /private ABC123DEF456")
            return

        code = args[1]

        if not valid_code(code):
            await message.answer("❌ ID должен быть 12 символов (буквы и цифры)")
            return

        # Проверка уникальности
        if not await is_unique_private_id(code):
            await message.answer("❌ Этот ID уже занят")
            return

        # Регистрация нового ID
        if uid not in users:
            users[uid] = {}

        users[uid]["private_id"] = code
        users[uid]["time_reg"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        users[uid].setdefault("status", "registered")

        await message.answer(f"✅ ID зарегистрирован:\n{code}")

# ---------- UNPRIVATE ----------
@dp.message(Command("unprivate"))
async def unprivate(message: Message):
    if not is_admin(message.from_user):
        await message.answer("❌ Нет доступа")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Используйте: /unprivate USER_ID")
        return

    target_uid = args[1]

    async with get_users() as users:
        if target_uid in users and users[target_uid].get("private_id"):
            del users[target_uid]["private_id"]
            await message.answer("✅ ID удалён")
        else:
            await message.answer("❌ Пользователь не найден или ID не установлен")

# ---------- МЕНЮ ----------
@dp.callback_query(lambda c: c.data == "buy")
async def buy(callback: types.CallbackQuery):
    await callback.message.edit_text("💰 Выбери способ оплаты:", reply_markup=buy_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.edit
