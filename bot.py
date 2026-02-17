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

# ---------- ENV ----------
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

# ---------- НАСТРОЙКИ ----------
ADMIN_ID = 335400441
PAYMENT_LINK = "https://www.tbank.ru/cf/7GlP75YQif6"
SUPPORT_LINK = "https://t.me/remvord"  # <-- без @

user_data = {}
pending_orders = {}

# ---------- ВСПОМОГАТЕЛЬНОЕ ----------
async def safe_send(message: Message, text: str, keyboard=None):
    chunk_size = 4000
    for i in range(0, len(text), chunk_size):
        await message.answer(
            text[i:i+chunk_size],
            reply_markup=keyboard if i == 0 else None
        )

# ---------- НУМЕРОЛОГИЯ ----------
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

    extra_digits = []
    for n in [s1, s2, s3, s4]:
        extra_digits.extend([int(d) for d in str(n)])

    all_digits = digits + extra_digits
    return {i: all_digits.count(i) for i in range(1, 10)}

# ---------- PDF ----------
def generate_pdf(user_id, birth_date, full_name, matrix_visual, analysis, short_version):
    filename = f"matrix_{user_id}.pdf"

    # Универсальный шрифт для Linux
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))

    doc = SimpleDocTemplate(filename, pagesize=A4)

    normal_style = ParagraphStyle(
        name='Normal',
        fontName='DejaVuSans',
        fontSize=11,
        leading=15,
    )

    header_style = ParagraphStyle(
        name='Header',
        fontName='DejaVuSans',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1F618D"),
        spaceAfter=14
    )

    section_style = ParagraphStyle(
        name='Section',
        fontName='DejaVuSans',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2E4053"),
        spaceBefore=14,
        spaceAfter=6
    )

    elements = []

    elements.append(Paragraph("Персональный нумерологический отчёт", header_style))
    elements.append(Paragraph(f"Дата рождения: {birth_date}", normal_style))
    elements.append(Paragraph(f"Имя: {full_name}", normal_style))
    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("Расширенный профиль", section_style))
    elements.append(Paragraph(short_version.replace("\n", "<br/>"), normal_style))
    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("Матрица Пифагора", section_style))
    elements.append(Paragraph(matrix_visual.replace("\n", "<br/>"), normal_style))
    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("Полный аналитический разбор", section_style))
    elements.append(Paragraph(analysis.replace("\n", "<br/>"), normal_style))

    doc.build(elements)
    return filename

# ---------- UI ----------
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
                text="🔁 Сделать новый расчёт",
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

# ---------- RUN ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
