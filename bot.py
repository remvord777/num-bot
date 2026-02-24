import asyncio
import os
import re
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import CommandStart
from openai import OpenAI


# ================== ENV ==================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден")

if not OPENAI_KEY:
    raise ValueError("OPENAI_KEY не найден")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_KEY)


# ================== НАСТРОЙКИ ==================

DONATE_LINK = "https://www.tbank.ru/cf/7GlP75YQif6"
SUPPORT_LINK = "https://t.me/remvord"


# ================== УТИЛИТЫ ==================

def reduce_number(n: int) -> int:
    while n > 9 and n not in (11, 22):
        n = sum(int(d) for d in str(n))
    return n


def valid_date(text: str):
    return bool(re.match(r"^\d{2}\.\d{2}\.\d{4}$", text.strip()))


# 🔥 ФИКСИРУЕМ СИСТЕМУ 1 / 5 / 9

def mission_number(day, month, year):
    total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
    return reduce_number(total)

def realization_number(day, month):
    total = sum(int(d) for d in f"{day:02d}{month:02d}")
    return reduce_number(total)

def consciousness_number(day):
    return reduce_number(day)


# ================== UI ==================

def get_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="💛 Сказать спасибо (99 ₽)",
                callback_data="thanks"
            )],
            [InlineKeyboardButton(
                text="🔁 Новый расчёт",
                callback_data="new_calc"
            )],
            [InlineKeyboardButton(
                text="💬 Поддержка",
                url=SUPPORT_LINK
            )]
        ]
    )


# ================== START ==================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Введите дату рождения в формате:\n"
        "ДД.ММ.ГГГГ\n"
        "Пример: 20.02.1967"
    )


# ================== РАСЧЁТ ==================

@dp.message()
async def calculate(message: Message):

    birth_date = message.text.strip()

    if not valid_date(birth_date):
        await message.answer("Введите дату в формате ДД.ММ.ГГГГ")
        return

    day, month, year = map(int, birth_date.split("."))

    mission = mission_number(day, month, year)
    realization = realization_number(day, month)
    consciousness = consciousness_number(day)

    prompt = f"""
Дата рождения: {birth_date}

Число миссии: {mission}
Число реализации: {realization}
Число сознания: {consciousness}

Сделай глубокий, структурированный разбор.
Без символов ###.
Используй красивые визуальные блоки и эмодзи.

Структура:

🔹 Число миссии — предназначение
🔹 Число реализации — проявление в жизни
🔹 Число сознания — тип мышления
🔹 Сильные стороны
🔹 Возможные тени
🔹 Финансовый потенциал
🔹 Итог

Пиши экспертно, эмоционально, но без воды.
Объём 1800–2500 символов.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты профессиональный нумеролог."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
        max_tokens=2000
    )

    await message.answer(
        response.choices[0].message.content +
        "\n\nЕсли разбор оказался полезным — можно поддержать проект 💛",
        reply_markup=get_menu()
    )


# ================== CALLBACK ==================

@dp.callback_query()
async def callbacks(callback: CallbackQuery):

    if callback.data == "new_calc":
        await callback.answer()
        await callback.message.answer(
            "Введите дату рождения в формате ДД.ММ.ГГГГ"
        )

    elif callback.data == "thanks":
        await callback.answer()

        await callback.message.answer(
            "💛 Спасибо за поддержку!\n\n"
            "Если хотите поддержать проект — 99 ₽ по ссылке ниже:"
        )

        await callback.message.answer(DONATE_LINK)


# ================== RUN ==================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())