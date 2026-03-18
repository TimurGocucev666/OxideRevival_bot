import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, LabeledPrice
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

PRICE = 100  # 100 stars

@dp.message(CommandStart())
async def start(message: Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="💎 Купить ЗБТ")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🎮 OxideRevival\n\n"
        "Доступ к ЗБТ — 100⭐\n\n"
        "Нажми кнопку ниже 👇",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text == "💎 Купить ЗБТ")
async def buy(message: Message):
    prices = [LabeledPrice(label="ЗБТ доступ", amount=100 * 100)]

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
    await message.answer(
        "✅ Оплата прошла!\n\n"
        "🎉 Ты получил доступ к ЗБТ OxideRevival"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
