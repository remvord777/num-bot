import asyncio
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    FSInputFile
)
from aiogram.filters import CommandStart
from openai import OpenAI

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors


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

ADMIN_ID = 335400441
PAYMENT_LINK = "https://www.tbank.ru/cf/7GlP75YQif6"
SUPPORT_LINK = "https://t.me/remvord"

user_data = {}
pending_orders = {}


# ================== SAFE SEND ==================

async def safe_send(message: Message, text: str, keyboard=None):
    chunk = 4000
    for i in range(0, len(text), chunk):
        await message.answer(
            text[i:i + chunk],
            reply_markup=keyboard if i == 0 else None
        )


# ================== НУМЕРОЛОГИЯ ==================

def reduce_number(n: int) -> int:
    while n > 9 and n not in (11, 22):
        n = sum(int(d) for d in str(n))
    return n


def life_path(day: int, month: int, year: int) -> int:
    total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
    return reduce_number(total)


def personal_year(day: int, month: int, current_year: int) -> int:
    total = sum(int(d) for d in f"{day:02d}{month:02d}{current_year}")
    return reduce_number(total)


def pythagoras_matrix(day: int, month: int, year: int):
    digits = [int(d) for d in f"{day:02d}{month:02d}{year}"]
    s1 = sum(digits)
    s2 = sum(int(d) for d in str(s1))
    s3 = s1 - (int(str(day)[0]) * 2)
    s4 = sum(int(d) for d in str(s3))

    extra = []
    for n in [s1, s2, s3, s4]:
        extra.extend([int(d) for d in str(n)])

    all_digits = digits + extra
    return {i: all_digits.count(i) for i in range(1, 10)}


# ================== PDF ==================

def generate_pdf(user_id, birth_date, full_name, matrix_visual, analysis):
    filename = f"/tmp/matrix_{user_id}.pdf"

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))

    doc = SimpleDocTemplate(filename, pagesize=A4)

    normal = ParagraphStyle(
        name='Normal',
        fontName='DejaVuSans',
        fontSize=11,
        leading=15
    )

    header = ParagraphStyle(
        name='Header',
        fontName='DejaVuSans',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1F618D"),
        spaceAfter=14
    )

    section = ParagraphStyle(
        name='Section',
        fontName='DejaVuSans',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2E4053"),
        spaceBefore=14,
        spaceAfter=6
    )

    elements = []

    elements.append(Paragraph("Персональный нумерологический отчёт", header))
    elements.append(Paragraph(f"Дата рождения: {birth_date}", normal))
    elements.append(Paragraph(f"Имя: {full_name}", normal))
    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("Матрица Пифагора", section))
    elements.append(Paragraph(matrix_visual.replace("\n", "<br/>"), normal))
    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("Полный аналитический разбор", section))
    elements.append(Paragraph(analysis.replace("\n", "<br/>"), normal))

    doc.build(elements)
    return filename


# ================== UI ==================

def get_pay_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔥 Получить расширенный PDF (399 ₽)",
                callback_data="buy_full"
            )],
            [InlineKeyboardButton(
                text="💬 Поддержка",
                url=SUPPORT_LINK
            )]
        ]
    )


def get_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
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


def valid_input(text: str):
    return "," in text and re.match(r"\d{2}\.\d{2}\.\d{4}", text.strip())


# ================== HANDLERS ==================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Введите дату и имя через запятую:\n\n"
        "Пример: 21.07.1987, Иван Петров",
        reply_markup=get_main_menu()
    )


@dp.message()
async def calculate(message: Message):
    text = message.text.strip()

    if not valid_input(text):
        await message.answer("Введите: ДД.ММ.ГГГГ, Имя Фамилия")
        return

    birth_date, full_name = map(str.strip, text.split(",", 1))
    day, month, year = map(int, birth_date.split("."))

    lp = life_path(day, month, year)
    py = personal_year(day, month, datetime.now().year)

    user_data[message.from_user.id] = {
        "birth_date": birth_date,
        "full_name": full_name
    }

    prompt = f"""
Дата рождения: {birth_date}
Число пути: {lp}
Персональный год: {py}

Сделай краткий нумерологический разбор.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты профессиональный нумеролог."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=800
    )

    await safe_send(message, response.choices[0].message.content, get_pay_keyboard())


@dp.callback_query()
async def callbacks(callback: CallbackQuery):

    if callback.data == "new_calc":
        await callback.answer()
        await callback.message.answer(
            "Введите дату и имя через запятую:\n\n"
            "Пример: 21.07.1987, Иван Петров"
        )

    elif callback.data == "buy_full":
        await callback.answer()

        await callback.message.answer(
            "Оплатите 399 ₽ по ссылке ниже.\n\n"
            "После оплаты нажмите кнопку."
        )

        await callback.message.answer(PAYMENT_LINK)

        await callback.message.answer(
            "Подтвердите оплату:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="✅ Я оплатил",
                        callback_data="confirm_payment"
                    )]
                ]
            )
        )

    elif callback.data == "confirm_payment":
        await callback.answer()

        data = user_data.get(callback.from_user.id)
        if not data:
            return

        pending_orders[callback.from_user.id] = data

        await callback.message.answer("⏳ Отправлено на проверку.")

        await bot.send_message(
            ADMIN_ID,
            f"💳 Запрос подтверждения\n\n"
            f"{data['birth_date']}\n"
            f"{data['full_name']}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Подтвердить",
                            callback_data=f"approve_{callback.from_user.id}"
                        )
                    ]
                ]
            )
        )

    elif callback.data.startswith("approve_") and callback.from_user.id == ADMIN_ID:

        user_id = int(callback.data.split("_")[1])
        data = pending_orders.get(user_id)
        if not data:
            return

        birth_date = data["birth_date"]
        full_name = data["full_name"]

        day, month, year = map(int, birth_date.split("."))
        matrix = pythagoras_matrix(day, month, year)

        matrix_visual = (
            f"{matrix[1]}  {matrix[4]}  {matrix[7]}\n"
            f"{matrix[2]}  {matrix[5]}  {matrix[8]}\n"
            f"{matrix[3]}  {matrix[6]}  {matrix[9]}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты профессиональный нумеролог."},
                {"role": "user", "content": f"Сделай полный разбор для {birth_date}."}
            ],
            temperature=0.8,
            max_tokens=1400
        )

        analysis = response.choices[0].message.content

        filename = generate_pdf(
            user_id,
            birth_date,
            full_name,
            matrix_visual,
            analysis
        )

        await bot.send_document(user_id, FSInputFile(filename))

        if os.path.exists(filename):
            os.remove(filename)

        await bot.send_message(
            user_id,
            "✅ Ваш отчёт готов.",
            reply_markup=get_main_menu()
        )

        await callback.message.edit_text("✅ Оплата подтверждена.")
        del pending_orders[user_id]


# ================== RUN ==================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
