import asyncio
import os
import re
import logging
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import CommandStart, Command
from openai import OpenAI


# ================== НАСТРОЙКИ ==================

ADMIN_ID = 335400441
DONATE_LINK = "https://www.tbank.ru/cf/7GlP75YQif6"
SUPPORT_LINK = "https://t.me/remvord"
KNOWN_USERS_FILE = "known_users.txt"


# ================== ЛОГИРОВАНИЕ ==================

logging.basicConfig(
    filename="users.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)


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


# ================== ВСПОМОГАТЕЛЬНЫЕ ==================

def reduce_number(n: int) -> int:
    while n > 9 and n not in (11, 22):
        n = sum(int(d) for d in str(n))
    return n


def parse_birth_date(text: str):
    text = text.strip()
    digits = re.sub(r"\D", "", text)

    if len(digits) != 8:
        return None

    day = int(digits[:2])
    month = int(digits[2:4])
    year = int(digits[4:])

    try:
        date = datetime(year, month, day)

        if year < 1900 or year > datetime.now().year:
            return None

        return date.strftime("%d.%m.%Y")

    except ValueError:
        return None


def mission_number(day, month, year):
    total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
    return reduce_number(total)


def realization_number(day, month):
    total = sum(int(d) for d in f"{day:02d}{month:02d}")
    return reduce_number(total)


def consciousness_number(day):
    return reduce_number(day)


def is_new_user(user_id: int):
    if not os.path.exists(KNOWN_USERS_FILE):
        return True

    with open(KNOWN_USERS_FILE, "r") as f:
        known = f.read().splitlines()

    return str(user_id) not in known


def save_user(user_id: int):
    with open(KNOWN_USERS_FILE, "a") as f:
        f.write(f"{user_id}\n")


# ================== UI ==================

def get_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="💛 Поддержать проект",
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

    user_id = message.from_user.id

    logging.info(
        f"START | ID: {user_id} | "
        f"Username: @{message.from_user.username} | "
        f"Name: {message.from_user.full_name}"
    )

    if is_new_user(user_id):
        save_user(user_id)

        await bot.send_message(
            ADMIN_ID,
            f"🔔 Новый пользователь\n\n"
            f"ID: {user_id}\n"
            f"Username: @{message.from_user.username}\n"
            f"Name: {message.from_user.full_name}"
        )

    await message.answer(
        "🔮 Введите дату рождения\n\n"
        "Можно так:\n"
        "20.02.1967\n"
        "20-02-1967\n"
        "20021967\n\n"
        "Я сам приведу к нужному формату."
    )


# ================== ADMIN STATS ==================

@dp.message(Command("stats"))
async def stats(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    total_users = 0
    total_calcs = 0
    total_donates = 0

    if os.path.exists(KNOWN_USERS_FILE):
        with open(KNOWN_USERS_FILE, "r") as f:
            total_users = len(f.read().splitlines())

    if os.path.exists("users.log"):
        with open("users.log", "r") as f:
            logs = f.read()
            total_calcs = logs.count("CALC |")
            total_donates = logs.count("DONATE_CLICK |")

    await message.answer(
        "📊 Статистика проекта:\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔢 Расчётов: {total_calcs}\n"
        f"💛 Клики доната: {total_donates}"
    )


# ================== РАСЧЁТ ==================

@dp.message(~Command())
async def calculate(message: Message):

    parsed_date = parse_birth_date(message.text)

    if not parsed_date:
        await message.answer(
            "❌ Неверная дата.\n\n"
            "Попробуйте снова.\n"
            "Пример: 20.02.1967"
        )
        return

    day, month, year = map(int, parsed_date.split("."))

    mission = mission_number(day, month, year)
    realization = realization_number(day, month)
    consciousness = consciousness_number(day)

    logging.info(
        f"CALC | ID: {message.from_user.id} | Date: {parsed_date}"
    )

    prompt = f"""
Дата рождения: {parsed_date}

Число миссии: {mission}
Число реализации: {realization}
Число сознания: {consciousness}

Сделай глубокий, структурированный разбор.
Используй эмодзи.
Объём 2000–3000 символов.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты профессиональный нумеролог."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
        max_tokens=2500
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
            "Введите дату рождения (любой формат):\n"
            "20.02.1967 или 20021967"
        )

    elif callback.data == "thanks":

        logging.info(
            f"DONATE_CLICK | ID: {callback.from_user.id}"
        )

        await bot.send_message(
            ADMIN_ID,
            f"💛 Донат-клик\n\n"
            f"ID: {callback.from_user.id}\n"
            f"Username: @{callback.from_user.username}\n"
            f"Name: {callback.from_user.full_name}"
        )

        await callback.answer()
        await callback.message.answer(
            "💛 Спасибо за поддержку!\n\n"
            "Если хотите поддержать проект — перейдите по ссылке:"
        )
        await callback.message.answer(DONATE_LINK)


# ================== RUN ==================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())