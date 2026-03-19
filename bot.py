import asyncio
import os
import json
import random
import string
from datetime import datetime
import re

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, LabeledPrice,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand
)
from aiogram.filters import CommandStart, Command

TOKEN = os.getenv("TOKEN")

# 👑 АДМИНЫ
ADMIN_IDS = [123456789]  # твой ID
ADMIN_USERNAMES = ["Durove14"]

ACCESS_LINK = "https://t.me/+s1xuxYDZbzxjNWZi"

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_FILE = "users.json"
PRICE_STARS = 75


# ---------- БАЗА ----------
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
    return bool(re.fullmatch(r"[A-Za-z0-9]{12}", code))


# ---------- АДМИН ----------
def is_admin(user):
    return (user.id in ADMIN_IDS) or (user.username in ADMIN_USERNAMES)


# ---------- UI ----------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить ЗБТ", callback_data="buy")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])

def buy_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Stars", callback_data="stars")],
        [InlineKeyboardButton(text="💳 Donation", url="https://dalink.to/bountygames3")],
        [InlineKeyboardButton(text="📸 Я оплатил", callback_data="proof")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])


# ---------- КОМАНДЫ ----------
async def set_commands():
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
    users = load_users()
    uid = str(message.from_user.id)

    args = message.text.split()

    if uid in users and "private_id" in users[uid] and len(args) == 1:
        data = users[uid]
        await message.answer(
            f"🆔 ID: {data.get('private_id')}\n"
            f"📅 Дата: {data.get('time_reg')}\n"
            f"💎 Статус: {data.get('status','-')}\n"
            f"🔑 Ключ: {data.get('key','нет')}"
        )
        return

    if len(args) != 2:
        await message.answer("❌ /private ABC123DEF456")
        return

    code = args[1]

    if not valid_code(code):
        await message.answer("❌ ID должен быть 12 символов")
        return

    if uid not in users:
        users[uid] = {}

    users[uid]["private_id"] = code
    users[uid]["time_reg"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_users(users)

    await message.answer(f"✅ ID зарегистрирован:\n{code}")


# ---------- UNPRIVATE ----------
@dp.message(Command("unprivate"))
async def unprivate(message: Message):
    if not is_admin(message.from_user):
        await message.answer("❌ Нет доступа")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ /unprivate USER_ID")
        return

    uid = args[1]
    users = load_users()

    if uid in users:
        users[uid]["private_id"] = None
        save_users(users)
        await message.answer("✅ ID удалён")
    else:
        await message.answer("❌ Не найден")


# ---------- МЕНЮ ----------
@dp.callback_query(lambda c: c.data == "buy")
async def buy(callback):
    await callback.message.edit_text("💰 Выбери оплату:", reply_markup=buy_menu())


@dp.callback_query(lambda c: c.data == "back")
async def back(callback):
    await callback.message.edit_text("Меню:", reply_markup=main_menu())


# ---------- STARS ----------
@dp.callback_query(lambda c: c.data == "stars")
async def stars(callback):
    prices = [LabeledPrice(label="ЗБТ", amount=PRICE_STARS)]

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="ЗБТ",
        description="Доступ",
        payload="zbt",
        provider_token="",
        currency="XTR",
        prices=prices,
    )


@dp.pre_checkout_query()
async def pre_checkout(q):
    await bot.answer_pre_checkout_query(q.id, ok=True)


@dp.message(lambda m: m.successful_payment)
async def success(message: Message):
    users = load_users()
    uid = str(message.from_user.id)

    if uid not in users:
        users[uid] = {}

    users[uid]["key"] = generate_key()
    users[uid]["status"] = "paid"

    save_users(users)

    await message.answer(
        f"✅ Оплачено!\n\n🔗 {ACCESS_LINK}"
    )


# ---------- СКРИН ----------
@dp.callback_query(lambda c: c.data == "proof")
async def proof(callback):
    await callback.message.answer("📸 Отправь скрин оплаты")


@dp.message(lambda m: m.photo)
async def photo(message: Message):
    users = load_users()
    uid = str(message.from_user.id)

    if uid not in users:
        users[uid] = {}

    users[uid]["status"] = "pending"
    save_users(users)

    text = (
        f"💸 Новая заявка\n"
        f"👤 @{message.from_user.username}\n"
        f"🆔 {uid}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅", callback_data=f"ok_{uid}"),
            InlineKeyboardButton(text="❌", callback_data=f"no_{uid}")
        ]
    ])

    # отправка ВСЕМ админам
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                photo=message.photo[-1].file_id,
                caption=text,
                reply_markup=kb
            )
        except:
            pass

    await message.answer("⏳ Отправлено на проверку")


# ---------- АДМИН ----------
@dp.callback_query(lambda c: c.data.startswith("ok_"))
async def ok(callback):
    uid = callback.data.split("_")[1]
    users = load_users()

    key = generate_key()
    users[uid]["key"] = key
    users[uid]["status"] = "paid"
    save_users(users)

    await bot.send_message(
        uid,
        f"✅ Оплата подтверждена!\n\n🔗 {ACCESS_LINK}"
    )

    await callback.message.edit_text("✅ OK")


@dp.callback_query(lambda c: c.data.startswith("no_"))
async def no(callback):
    uid = callback.data.split("_")[1]

    await bot.send_message(uid, "❌ Отклонено")
    await callback.message.edit_text("❌ NO")


# ---------- ПРОФИЛЬ ----------
@dp.callback_query(lambda c: c.data == "profile")
async def profile(callback):
    users = load_users()
    uid = str(callback.from_user.id)

    if uid not in users:
        await callback.message.answer("❌ Нет данных")
        return

    d = users[uid]

    await callback.message.answer(
        f"👤 Профиль\n\n"
        f"🆔 ID: {d.get('private_id','нет')}\n"
        f"💎 Статус: {d.get('status','-')}\n"
        f"🔑 Ключ: {d.get('key','нет')}"
    )


# ---------- ЗАПУСК ----------
async def main():
    await set_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
