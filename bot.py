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
ADMIN_IDS = [7728468302]  # ВСТАВЬ СВОЙ ID
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
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ---------- УТИЛИТЫ ----------
def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

def valid_code(code):
    return bool(re.fullmatch(r"[A-Za-z0-9]{12}", code))

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
        [InlineKeyboardButton(text="⭐ Оплата Stars", callback_data="stars")],
        [InlineKeyboardButton(text="💳 DonationAlerts", url="https://dalink.to/bountygames3")],
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
        "💰 <b>75⭐ или 100₽</b>\n\n"
        "⚡ Быстрая покупка\n"
        "🔐 Уникальный доступ\n\n"
        "👇 Выбери действие:",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ---------- PRIVATE ----------
@dp.message(Command("private"))
async def private_cmd(message: Message):
    users = load_users()
    uid = str(message.from_user.id)
    args = message.text.split()

    # показать инфу
    if uid in users and "private_id" in users[uid] and len(args) == 1:
        d = users[uid]
        await message.answer(
            f"👤 <b>Твой профиль</b>\n\n"
            f"🆔 ID: {d.get('private_id')}\n"
            f"📅 Дата: {d.get('time_reg')}\n"
            f"💎 Статус: {d.get('status','-')}\n"
            f"🔑 Ключ: {d.get('key','нет')}",
            parse_mode="HTML"
        )
        return

    if len(args) != 2:
        await message.answer("❌ Пример: /private ABC123DEF456")
        return

    code = args[1]

    if not valid_code(code):
        await message.answer("❌ ID должен быть 12 символов (A-Z 0-9)")
        return

    # проверка уникальности
    for u in users.values():
        if u.get("private_id") == code:
            await message.answer("❌ Этот ID уже занят")
            return

    if uid not in users:
        users[uid] = {}

    users[uid]["private_id"] = code
    users[uid]["time_reg"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    users[uid]["status"] = "registered"

    save_users(users)

    await message.answer(f"✅ ID зарегистрирован:\n<code>{code}</code>", parse_mode="HTML")


# ---------- UNPRIVATE ----------
@dp.message(Command("unprivate"))
async def unprivate(message: Message):
    if not is_admin(message.from_user):
        await message.answer("❌ Нет доступа")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Используй: /unprivate USER_ID")
        return

    uid = args[1]
    users = load_users()

    if uid in users and users[uid].get("private_id"):
        users[uid]["private_id"] = None
        save_users(users)
        await message.answer("✅ ID удалён")
    else:
        await message.answer("❌ Пользователь не найден")


# ---------- МЕНЮ ----------
@dp.callback_query(lambda c: c.data == "buy")
async def buy(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💰 <b>Выбери способ оплаты:</b>",
        parse_mode="HTML",
        reply_markup=buy_menu()
    )


@dp.callback_query(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.edit_text("🎮 Главное меню", reply_markup=main_menu())


# ---------- STARS ----------
@dp.callback_query(lambda c: c.data == "stars")
async def stars(callback: types.CallbackQuery):
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

    if uid not in users:
        users[uid] = {}

    users[uid]["status"] = "paid"
    users[uid]["key"] = generate_key()

    save_users(users)

    await message.answer(
        f"✅ <b>Оплата прошла!</b>\n\n"
        f"🔗 Доступ:\n{ACCESS_LINK}",
        parse_mode="HTML"
    )


# ---------- СКРИН ----------
@dp.callback_query(lambda c: c.data == "proof")
async def proof(callback: types.CallbackQuery):
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
        f"💸 <b>Новая заявка</b>\n\n"
        f"👤 @{message.from_user.username}\n"
        f"🆔 {uid}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ok_{uid}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"no_{uid}")
        ]
    ])

    success = False

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                photo=message.photo[-1].file_id,
                caption=text,
                parse_mode="HTML",
                reply_markup=kb
            )
            success = True
        except:
            pass

    if success:
        await message.answer("⏳ Отправлено на проверку")
    else:
        await message.answer("❌ Админ не открыл бота")


# ---------- АДМИН ----------
@dp.callback_query(lambda c: c.data.startswith("ok_"))
async def ok(callback: types.CallbackQuery):
    uid = callback.data.split("_")[1]
    users = load_users()

    users[uid]["status"] = "paid"
    users[uid]["key"] = generate_key()

    save_users(users)

    await bot.send_message(
        uid,
        f"✅ <b>Оплата подтверждена!</b>\n\n"
        f"🔗 {ACCESS_LINK}",
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
        f"🆔 ID: {d.get('private_id','нет')}\n"
        f"💎 Статус: {d.get('status','-')}\n"
        f"🔑 Ключ: {d.get('key','нет')}",
        parse_mode="HTML"
    )


# ---------- ЗАПУСК ----------
async def main():
    await set_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
