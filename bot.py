import asyncio
import os
import re
from typing import Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# ---------- Конфигурация ----------
TOKEN = os.getenv("8785149097:AAGl_nJTi9LgMXdERKonwhnOzYtW87T7Li0")                     # токен бота
SBP_LINK = os.getenv("SBP_LINK", "https://example.com/pay")  # ссылка на оплату СБП
STARS_PRICE = int(os.getenv("STARS_PRICE", 100))             # цена в звёздах
INVITE_LINK = "https://t.me/+s1xuxYDZbzxjNWZi"              # ссылка на закрытый канал

# Хранилища (в реальном проекте заменить на БД)
user_registrations: Dict[int, str] = {}   # зарегистрированные коды
granted_access: Dict[int, bool] = {}       # кому уже выдан доступ

# ---------- Инициализация ----------
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ---------- Вспомогательные функции ----------
def is_valid_code(code: str) -> bool:
    """Проверяет, что код состоит из 8 символов (англ. буквы + цифры)"""
    return bool(re.fullmatch(r"[A-Za-z0-9]{8}", code))

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Купить за Stars", callback_data="buy_stars")
    builder.button(text="💳 Купить по СБП", callback_data="sbp")
    builder.button(text="📝 Регистрация ID", callback_data="register_info")
    builder.adjust(1)
    return builder.as_markup()

# ---------- Команда /start ----------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "🎮 <b>OxideRevival</b> — закрытый бета‑тест\n\n"
        "🔥 <i>Получи доступ к игре первым!</i>\n\n"
        f"⭐ Цена доступа: <b>{STARS_PRICE} звёзд</b>\n"
        "💳 Также доступна оплата по СБП\n\n"
        "👇 Выберите действие:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

# ---------- Обработчики inline-кнопок ----------
@dp.callback_query(F.data == "buy_stars")
async def callback_buy_stars(callback: CallbackQuery):
    """Оплата звёздами"""
    prices = [LabeledPrice(label="ЗБТ OxideRevival", amount=STARS_PRICE)]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="⚡ Доступ к ЗБТ",
        description="Оплата звёздами Telegram",
        payload="zbt_access",
        provider_token="",
        currency="XTR",
        prices=prices,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="💎 Оплатить", pay=True)]]
        )
    )
    await callback.answer()

@dp.callback_query(F.data == "sbp")
async def callback_sbp(callback: CallbackQuery):
    """Оплата по СБП (выдаётся вручную)"""
    text = (
        "💳 <b>Оплата по СБП</b>\n\n"
        "Перейдите по ссылке ниже и выполните перевод:\n"
        f"🔗 {SBP_LINK}\n\n"
        "После оплаты напишите администратору @support и пришлите скриншот для подтверждения.\n"
        "Доступ будет выдан вручную."
    )
    await callback.message.answer(text, disable_web_page_preview=True)
    await callback.answer()

@dp.callback_query(F.data == "register_info")
async def callback_register_info(callback: CallbackQuery):
    """Информация о регистрации по коду"""
    text = (
        "📝 <b>Регистрация по коду</b>\n\n"
        "Если у вас есть 8‑значный код (английские буквы и цифры), "
        "введите команду:\n"
        "<code>/register КОД</code>\n\n"
        "Например: <code>/register Abc12345</code>"
    )
    await callback.message.answer(text)
    await callback.answer()

# ---------- Команда /register ----------
@dp.message(Command("register"))
async def cmd_register(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите код после команды. Пример:\n<code>/register Abc12345</code>")
        return

    code = args[1].strip()
    if not is_valid_code(code):
        await message.answer(
            "❌ Неверный формат кода.\n"
            "Код должен состоять ровно из 8 символов: латинские буквы (A-Z, a-z) и цифры (0-9)."
        )
        return

    user_id = message.from_user.id
    if user_id in user_registrations:
        await message.answer("⚠️ Вы уже зарегистрировали код. Один пользователь — один код.")
        return

    user_registrations[user_id] = code
    await message.answer(
        f"✅ Код <code>{code}</code> успешно зарегистрирован!\n"
        "Теперь вы можете приобрести доступ."
    )

# ---------- Обработка платежей ----------
@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    """Выдача ссылки после успешной оплаты звёздами"""
    user_id = message.from_user.id

    # Проверяем, не выдавали ли доступ ранее
    if user_id in granted_access and granted_access[user_id]:
        await message.answer(
            "🔁 Вы уже активировали доступ ранее. Ссылка на канал уже должна быть у вас.\n"
            "Если вы потеряли ссылку, обратитесь к @support."
        )
        return

    # Отправляем ссылку
    await message.answer(
        f"🎉 <b>Оплата подтверждена!</b>\n\n"
        f"🔗 Ваша ссылка для вступления в закрытый канал ЗБТ:\n"
        f"{INVITE_LINK}\n\n"
        f"👉 Перейдите по ней и присоединяйтесь к сообществу тестеров!\n\n"
        f"<i>Ссылка одноразовая? Если возникнут проблемы, напишите @support.</i>"
    )

    # Помечаем доступ как выданный
    granted_access[user_id] = True

# ---------- (Опционально) Команда для административной выдачи доступа ----------
@dp.message(Command("give_access"))
async def cmd_give_access(message: Message):
    """Команда для администратора: /give_access @username (выдаёт ссылку указанному пользователю)"""
    # Простейшая проверка на админа (замените на свою логику)
    if message.from_user.id not in [123456789]:  # ID администратора
        await message.answer("⛔ У вас нет прав на эту команду.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажите username. Пример:\n/give_access @durov")
        return

    username = args[1].strip().lstrip('@')
    try:
        # Пытаемся получить информацию о пользователе
        user = await bot.get_chat(f"@{username}")
        user_id = user.id

        if user_id in granted_access and granted_access[user_id]:
            await message.answer(f"Пользователь @{username} уже получал доступ.")
            return

        # Отправляем ссылку пользователю
        await bot.send_message(
            user_id,
            f"🎁 Администратор выдал вам доступ к ЗБТ!\n\n"
            f"🔗 Ссылка для входа:\n{INVITE_LINK}"
        )
        granted_access[user_id] = True
        await message.answer(f"✅ Доступ выдан пользователю @{username}.")
    except TelegramBadRequest:
        await message.answer("❌ Не удалось найти пользователя или он не начал диалог с ботом.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# ---------- Запуск ----------
async def main():
    print("🚀 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
