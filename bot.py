import asyncio
import os
import json
import random
import string
import re

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, LabeledPrice,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command

TOKEN = os.getenv("TOKEN")
CHAT_ID = -1003782395593  # ВАЖНО: твой канал

bot = Bot(token=TOKEN)
dp = Dispatcher()

PRICE = 100  # ⭐ ИСПРАВЛЕНО
DB_FILE = "users.json"

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


# --- команды ---
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


@dp.callback_query(lambda c: c.data == "access")
async def access(callback: types.CallbackQuery):
    users = load_users()
    user_id = str(callback.from_user.id)

    if user_id in users:
        data = users[user_id]
        await callback.message.answer(
            f"🔑 <b>Твой ключ:</b>\n<code>{data['key']}</code>\n\n"
            f"🆔 Твой ID: <code>{data.get('private_id', 'не задан')}</code>",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer("❌ У тебя нет доступа")


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
        "private_id": None
    }

    save_users(users)

    await message.answer(
        f"✅ Оплата прошла!\n\n"
        f"🔑 Твой ключ:\n<code>{key}</code>\n\n"
        "📩 Введи команду:\n"
        "<code>/private ТВОЙ_ID</code>",
        parse_mode="HTML"
    )


# --- регистрация ---
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
        await message.answer("❌ Сначала купи доступ")
        return

    # проверка подписки
    member = await bot.get_chat_member(CHAT_ID, message.from_user.id)
    if member.status in ["left", "kicked"]:
        await message.answer("❌ Сначала вступи в закрытый чат")
        return

    users[user_id]["private_id"] = code
    save_users(users)

    await message.answer(
        f"✅ ID сохранён!\n\n"
        f"🆔 <code>{code}</code>",
        parse_mode="HTML"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
