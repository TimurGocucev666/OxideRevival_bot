import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ===== НАСТРОЙКИ =====
TOKEN = "8785149097:AAGl_nJTi9LgMXdERKonwhnOzYtW87T7Li0"
CHANNEL_ID = -1001234567890
PRICE = 100  # Stars

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ===== ВРЕМЕННОЕ ХРАНИЛИЩЕ =====
user_codes = {}
user_access = {}

# ===== ПРОВЕРКА КОДА =====
def is_valid_code(code: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]{8}", code))

# ===== КНОПКИ =====
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Купить доступ", callback_data="buy")
    kb.button(text="📝 Ввести код", callback_data="code")
    kb.adjust(1)
    return kb.as_markup()

# ===== СТАРТ =====
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        f"🎮 <b>Доступ к ЗБТ</b>\n\n"
        f"⭐ Цена: <b>{PRICE} stars</b>\n\n"
        "👇 Выберите действие:",
        reply_markup=main_menu()
    )

# ===== ЗАПРОС КОДА =====
@dp.callback_query(F.data == "code")
async def request_code(callback: CallbackQuery):
    await callback.message.answer("Введите код (8 символов):")
    await callback.answer()

# ===== ОБРАБОТКА ВВОДА =====
@dp.message()
async def handle_message(message: Message):
    text = message.text.strip()

    if not is_valid_code(text):
        return

    user_id = message.from_user.id

    if user_id in user_codes:
        await message.answer("❗ Вы уже вводили код")
        return

    user_codes[user_id] = text
    await message.answer(f"✅ Код <code>{text}</code> успешно принят!")

# ===== ПОКУПКА =====
@dp.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    user_id = callback.from_user.id

    if user_access.get(user_id):
        await callback.answer("Вы уже купили доступ", show_alert=True)
        return

    if user_id not in user_codes:
        await callback.answer("Сначала введите код", show_alert=True)
        return

    prices = [LabeledPrice(label="Доступ к ЗБТ", amount=PRICE)]

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Доступ к ЗБТ",
        description="Оплата через Telegram Stars",
        payload="buy_access",
        provider_token="",
        currency="XTR",
        prices=prices,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="💎 Оплатить", pay=True)]]
        )
    )

    await callback.answer()

# ===== ПРЕДЧЕК =====
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# ===== УСПЕШНАЯ ОПЛАТА =====
@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    user_id = message.from_user.id

    if user_access.get(user_id):
        return

    # создаём одноразовую ссылку
    invite = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        member_limit=1
    )

    await message.answer(
        "🎉 <b>Оплата прошла успешно!</b>\n\n"
        f"🔗 Ваша ссылка для входа:\n{invite.invite_link}"
    )

    user_access[user_id] = True

# ===== ЗАПУСК =====
async def main():
    print("🚀 Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
