import asyncio
import os
import json
import random
import string

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, LabeledPrice
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

PRICE = 100  # 100 stars
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


# --- команды ---
@dp.message(CommandStart())
async def start(message: Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="💎 Купить ЗБТ")],
            [types.KeyboardButton(text="📦 Мой доступ")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "🎮 OxideRevival\n\n"
        "💰 Цена ЗБТ: 100⭐\n"
        "🔐 После оплаты ты получишь ключ\n\n"
        "👇 Выбери действие:",
        reply_markup=keyboard
    )


@dp.message(lambda m: m.text == "📦 Мой доступ")
async def my_access(message: Message):
    users = load_users()
    user_id = str(message.from_user.id)

    if user_id in users:
        await message.answer(f"🔑 Твой ключ:\n{users[user_id]}")
    else:
        await message.answer("❌ У тебя нет доступа")


@dp.message(lambda m: m.text == "💎 Купить ЗБТ")
async def buy(message: Message):
    users = load_users()
    user_id = str(message.from_user.id)

    if user_id in users:
        await message.answer("✅ Ты уже купил ЗБТ\nНажми «Мой доступ»")
        return

    prices = [LabeledPrice(label="ЗБТ доступ", amount=PRICE * 100)]

    await bot.send_invoice(
        chat_id=message.chat.id,
        title="ЗБТ OxideRevival",
        description="Доступ к закрытому тесту",
        payload="zbt_access",
        provider_token="",
        currency="XTR",
        prices=prices,
    )


@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@dp.message(lambda message: message.successful_payment)
async def success(message: Message):
    users = load_users()
    user_id = str(message.from_user.id)

    key = generate_key()
    users[user_id] = key
    save_users(users)

    await message.answer(
        "✅ Оплата прошла!\n\n"
        f"🔑 Твой ключ:\n{key}\n\n"
        "⚠️ Сохрани его!"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
