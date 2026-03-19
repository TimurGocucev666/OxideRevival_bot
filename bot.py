import asyncio
import os
import json
import random
import string
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, LabeledPrice,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 123456789  # ВСТАВЬ СВОЙ ID

DONATE_LINK = "https://dalink.to/bountygames3"

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_FILE = "users.json"
ADMIN_PASSWORD = "Bounty"

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


# ---------- UI ----------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить ЗБТ", callback_data="buy")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="ℹ️ О проекте", callback_data="info")]
    ])

def buy_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Оплатить Stars", callback_data="pay_stars")],
        [InlineKeyboardButton(text="💳 DonationAlerts", url=DONATE_LINK)],
        [InlineKeyboardButton(text="📸 Я оплатил", callback_data="send_proof")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])


# ---------- СТАРТ ----------
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎮 <b>OxideRevival</b>\n\n"
        "🔥 Закрытый Бета Тест\n"
        "💰 Цена: <b>75⭐ или 100₽</b>\n\n"
        "✨ Быстрая покупка и моментальная выдача\n\n"
        "👇 Выбери действие:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ---------- МЕНЮ ----------
@dp.callback_query(lambda c: c.data == "buy")
async def buy(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💰 <b>Выбери способ оплаты:</b>\n\n"
        "⭐ Stars — мгновенно\n"
        "💳 DonationAlerts — вручную",
        reply_markup=buy_menu(),
        parse_mode="HTML"
    )


@dp.callback_query(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎮 <b>OxideRevival</b>\n\nВыбери действие:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ---------- STARS ----------
@dp.callback_query(lambda c: c.data == "pay_stars")
async def pay_stars(callback: types.CallbackQuery):
    prices = [LabeledPrice(label="ЗБТ доступ", amount=PRICE_STARS)]

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="ЗБТ OxideRevival",
        description="Доступ к игре",
        payload="zbt",
        provider_token="",
        currency="XTR",
        prices=prices,
    )


@dp.pre_checkout_query()
async def pre_checkout(q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)


@dp.message(lambda m: m.successful_payment)
async def success(message: Message):
    users = load_users()
    uid = str(message.from_user.id)

    key = generate_key()

    users[uid] = {
        "key": key,
        "status": "paid",
        "username": message.from_user.username,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_users(users)

    await message.answer(
        f"✅ <b>Оплата прошла!</b>\n\n"
        f"🔑 Твой ключ:\n<code>{key}</code>",
        parse_mode="HTML"
    )


# ---------- DONATE ----------
@dp.callback_query(lambda c: c.data == "send_proof")
async def send_proof(callback: types.CallbackQuery):
    await callback.message.answer(
        "📸 <b>Отправь скрин оплаты</b>\n\n"
        "После проверки ты получишь доступ",
        parse_mode="HTML"
    )


@dp.message(lambda m: m.photo)
async def handle_photo(message: Message):
    users = load_users()
    uid = str(message.from_user.id)

    users[uid] = {
        "status": "pending",
        "username": message.from_user.username,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_users(users)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ok_{uid}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"no_{uid}")
        ]
    ])

    await bot.send_photo(
        ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=f"💸 Новая оплата\nID: {uid}",
        reply_markup=kb
    )

    await message.answer("⏳ Отправлено на проверку")


# ---------- АДМИН ----------
@dp.callback_query(lambda c: c.data.startswith("ok_"))
async def ok(callback: types.CallbackQuery):
    uid = callback.data.split("_")[1]
    users = load_users()

    key = generate_key()
    users[uid]["key"] = key
    users[uid]["status"] = "paid"

    save_users(users)

    await bot.send_message(
        uid,
        f"✅ Оплата подтверждена\n🔑 Ключ:\n<code>{key}</code>",
        parse_mode="HTML"
    )

    await callback.message.edit_text("✅ Подтверждено")


@dp.callback_query(lambda c: c.data.startswith("no_"))
async def no(callback: types.CallbackQuery):
    uid = callback.data.split("_")[1]

    await bot.send_message(uid, "❌ Оплата отклонена")
    await callback.message.edit_text("❌ Отклонено")


# ---------- ПРОФИЛЬ ----------
@dp.callback_query(lambda c: c.data == "profile")
async def profile(callback: types.CallbackQuery):
    users = load_users()
    uid = str(callback.from_user.id)

    if uid not in users:
        await callback.message.answer("❌ Нет данных")
        return

    d = users[uid]

    await callback.message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"Username: @{d.get('username','-')}\n"
        f"Статус: {d.get('status','-')}\n"
        f"Ключ: {d.get('key','нет')}\n"
        f"Дата: {d.get('time','-')}",
        parse_mode="HTML"
    )


# ---------- ИНФО ----------
@dp.callback_query(lambda c: c.data == "info")
async def info(callback: types.CallbackQuery):
    await callback.message.answer(
        "ℹ️ <b>OxideRevival</b>\n\n"
        "Это закрытый тест проекта\n"
        "Покупая доступ — ты поддерживаешь разработку ❤️",
        parse_mode="HTML"
    )


# ---------- АДМИНКА ----------
@dp.message(Command("admin"))
async def admin(message: Message):
    args = message.text.split()

    if len(args) != 2 or args[1] != ADMIN_PASSWORD:
        await message.answer("❌ Неверный пароль")
        return

    users = load_users()

    text = "👑 <b>Пользователи:</b>\n\n"
    for uid, d in users.items():
        text += f"{uid} | {d.get('status')} | {d.get('key','-')}\n"

    await message.answer(text, parse_mode="HTML")


# ---------- ЗАПУСК ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
