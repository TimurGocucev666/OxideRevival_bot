import asyncio
import os
import json
import random
import string
from datetime import datetime
import re

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

PRICE = 100  # ⭐ ЗБТ
DB_FILE = "users.json"
ADMIN_PASSWORD = "Bounty"

# --- база ---
def load_users():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

def valid_code(code):
    return bool(re.fullmatch(r"[A-Za-z0-9]{8}", code))

# --- UI ---
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить ЗБТ", callback_data="buy")],
        [InlineKeyboardButton(text="📦 Мой доступ", callback_data="access")]
    ])

# --- старт ---
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎮 <b>OxideRevival</b>\n\n"
        "🔐 Доступ к ЗБТ\n"
        "💰 Цена: <b>100⭐</b>\n\n"
        "👇 Выбери действие:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# --- просмотр доступа ---
@dp.callback_query(lambda c: c.data == "access")
async def access(callback: types.CallbackQuery):
    users = load_users()
    user_id = str(callback.from_user.id)

    if user_id in users:
        data = users[user_id]
        msg = f"🔑 <b>Твой ключ:</b>\n<code>{data['key']}</code>\n" \
              f"🆔 Private ID: <code>{data.get('private_id','не задан')}</code>\n" \
              f"⏱ Время регистрации: {data.get('registered','не задано')}\n" \
              f"👤 Username: @{data.get('username','-')}\n" \
              f"Имя: {data.get('first_name','-')} Фамилия: {data.get('last_name','-')}\n" \
              f"Язык: {data.get('language','-')}\n" \
              f"Статус: {data.get('status','-')}"
        await callback.message.answer(msg, parse_mode="HTML")
    else:
        await callback.message.answer("❌ У тебя нет доступа")

# --- купить ЗБТ ---
@dp.callback_query(lambda c: c.data == "buy")
async def buy(callback: types.CallbackQuery):
    users = load_users()
    user_id = str(callback.from_user.id)

    if user_id in users:
        await callback.message.answer("✅ Ты уже купил доступ")
        return

    prices = [LabeledPrice(label="ЗБТ доступ", amount=PRICE)]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="ЗБТ OxideRevival",
        description="Доступ к закрытому тесту",
        payload="zbt_access",
        provider_token="",
        currency="XTR",
        prices=prices,
    )

# --- оплата ---
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(lambda m: m.successful_payment)
async def success(message: Message):
    users = load_users()
    user_id = str(message.from_user.id)
    key = generate_key()

    users[user_id] = {
        "key": key,
        "private_id": None,
        "registered": None,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "language": message.from_user.language_code,
        "status": "paid"
    }
    save_users(users)

    await message.answer(
        f"✅ Оплата прошла!\n\n"
        f"🔑 Твой ключ: <code>{key}</code>\n"
        f"📩 Введи команду:\n<code>/private ТВОЙ_ID</code>",
        parse_mode="HTML"
    )

# --- регистрация через /private ---
@dp.message(Command("private"))
async def private_cmd(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Используй: /private ABC12345")
        return

    code = args[1]
    if not valid_code(code):
        await message.answer("❌ ID должен быть 8 символов (буквы+цифры)")
        return

    users = load_users()
    user_id = str(message.from_user.id)

    if user_id not in users:
        # если пользователь ещё не оплатил, всё равно регистрируем
        users[user_id] = {
            "key": None,
            "private_id": code,
            "registered": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "language": message.from_user.language_code,
            "status": "registered"
        }
    else:
        users[user_id]["private_id"] = code
        users[user_id]["registered"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_users(users)
    await message.answer(
        f"✅ Успешно зарегистрирован!\n\n"
        f"🆔 ID: <code>{code}</code>\n"
        f"⏱ Время регистрации: {users[user_id]['registered']}\n"
        f"👤 Username: @{users[user_id].get('username','-')}\n"
        f"Имя: {users[user_id].get('first_name','-')} Фамилия: {users[user_id].get('last_name','-')}\n"
        f"Язык: {users[user_id].get('language','-')}\n"
        f"Статус: {users[user_id].get('status','-')}",
        parse_mode="HTML"
    )

# --- админка ---
@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    args = message.text.split()
    if len(args) != 2 or args[1] != ADMIN_PASSWORD:
        await message.answer("❌ Неверный пароль")
        return

    users = load_users()
    if not users:
        await message.answer("📦 Нет зарегистрированных пользователей")
        return

    msg = "👑 <b>Список пользователей</b>\n\n"
    for uid, data in users.items():
        msg += (f"ID: <code>{uid}</code>\n"
                f"Ключ: <code>{data.get('key','-')}</code>\n"
                f"Private ID: <code>{data.get('private_id','-')}</code>\n"
                f"Время регистрации: {data.get('registered','-')}\n"
                f"Username: @{data.get('username','-')}\n"
                f"Имя: {data.get('first_name','-')} Фамилия: {data.get('last_name','-')}\n"
                f"Язык: {data.get('language','-')}\n"
                f"Статус: {data.get('status','-')}\n"
                "--------------------\n")
    await message.answer(msg, parse_mode="HTML")

# --- запуск ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
