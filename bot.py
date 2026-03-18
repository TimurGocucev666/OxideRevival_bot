import asyncio
import os
import re
from typing import Dict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ---------- CONFIG ----------
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = -1001234567890  # ID закрытого канала
SBP_LINK = os.getenv("SBP_LINK", "https://example.com/pay")
STARS_PRICE = 100

# ---------- STORAGE (замени на БД) ----------
user_codes: Dict[int, str] = {}
has_access: Dict[int, bool] = {}

# ---------- INIT ----------
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ---------- UTILS ----------
def valid_code(code: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]{8}", code))


def main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Купить за Stars", callback_data="buy")
    kb.button(text="💳 СБП", callback_data="sbp")
    kb.button(text="📝 Ввести код", callback_data="code")
    kb.adjust(1)
    return kb.as_markup()

# ---------- START ----------
@dp.message(CommandStart())
async def start(msg: Message):
    await msg.answer(
        "🎮 <b>OxideRevival — ЗБТ</b>\n\n"
        f"⭐ Цена: <b>{STARS_PRICE} stars</b>\n\n"
        "👇 Выберите:",
        reply_markup=main_kb()
    )

# ---------- REGISTER CODE ----------
@dp.callback_query(F.data == "code")
async def ask_code(call: CallbackQuery):
    await call.message.answer("Введите код (8 символов):")
    await call.answer()


@dp.message()
async def handle_code(msg: Message):
    code = msg.text.strip()

    if not valid_code(code):
        return

    if msg.from_user.id in user_codes:
        await msg.answer("❗ Вы уже вводили код")
        return

    user_codes[msg.from_user.id] = code
    await msg.answer(f"✅ Код <code>{code}</code> принят!")

# ---------- BUY ----------
@dp.callback_query(F.data == "buy")
async def buy(call: CallbackQuery):
    user_id = call.from_user.id

    if has_access.get(user_id):
        await call.answer("Вы уже купили доступ", show_alert=True)
        return

    if user_id not in user_codes:
        await call.answer("Сначала введите код", show_alert=True)
        return

    prices = [LabeledPrice(label="Доступ", amount=STARS_PRICE)]

    await bot.send_invoice(
        chat_id=call.message.chat.id,
        title="Доступ к ЗБТ",
        description="Оплата Stars",
        payload="access",
        provider_token="",
        currency="XTR",
        prices=prices,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Оплатить", pay=True)]]
        )
    )

    await call.answer()

# ---------- SBP ----------
@dp.callback_query(F.data == "sbp")
async def sbp(call: CallbackQuery):
    await call.message.answer(
        f"💳 Оплата:\n{SBP_LINK}\n\nПосле оплаты напишите @support"
    )
    await call.answer()

# ---------- PAYMENT ----------
@dp.pre_checkout_query()
async def pre_checkout(q):
    await bot.answer_pre_checkout_query(q.id, ok=True)


@dp.message(F.successful_payment)
async def success(msg: Message):
    user_id = msg.from_user.id

    if has_access.get(user_id):
        return

    # 🔥 создаём одноразовую ссылку
    invite = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        member_limit=1
    )

    await msg.answer(
        "🎉 Оплата прошла!\n\n"
        f"🔗 Ваша ссылка:\n{invite.invite_link}"
    )

    has_access[user_id] = True

# ---------- ADMIN ----------
ADMIN_ID = 123456789

@dp.message(Command("give_access"))
async def give_access(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return await msg.answer("Нет прав")

    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        return await msg.answer("Пример: /give_access 123456789")

    user_id = int(args[1])

    invite = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        member_limit=1
    )

    await bot.send_message(
        user_id,
        f"🎁 Вам выдан доступ:\n{invite.invite_link}"
    )

    has_access[user_id] = True
    await msg.answer("Готово")

# ---------- RUN ----------
async def main():
    print("🚀 Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
