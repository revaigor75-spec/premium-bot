import asyncio
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery
)

TOKEN = "8620057655:AAG1oMogyI46UKw7LQ4_yp2pHAEKwCTHc_w"

CHANNEL_ID=-1003949179855

bot = Bot(token=TOKEN)
dp = Dispatcher()

db = sqlite3.connect("users.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    end_date TEXT
)
""")

db.commit()

keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Пробный период", callback_data="trial")],
        [InlineKeyboardButton(text="⭐ 1 день — 20 Stars", callback_data="buy_1")],
        [InlineKeyboardButton(text="💎 7 дней — 100 Stars", callback_data="buy_7")],
        [InlineKeyboardButton(text="👑 30 дней — 300 Stars", callback_data="buy_30")]
    ]
)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "✨ Добро пожаловать в Premium Bot!\n\n"
        "📺 Здесь можно купить доступ в приватный канал.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "trial")
async def trial(callback):
    expire = datetime.now() + timedelta(days=2)

    cursor.execute(
        "INSERT INTO users VALUES (?, ?)",
        (callback.from_user.id, expire.strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.commit()

    link = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        member_limit=1
    )

    await callback.message.answer(
        f"🎁 Пробный доступ на 2 дня активирован!\n\n🔗 {link.invite_link}"
    )

@dp.callback_query(F.data == "buy_1")
async def buy1(callback):
    prices = [LabeledPrice(label="1 день", amount=20)]

    await bot.send_invoice(
        callback.from_user.id,
        title="⭐ Подписка на 1 день",
        description="Доступ в приватный канал на 1 день",
        payload="sub_1",
        provider_token="",
        currency="XTR",
        prices=prices
    )

@dp.callback_query(F.data == "buy_7")
async def buy7(callback):
    prices = [LabeledPrice(label="7 дней", amount=100)]

    await bot.send_invoice(
        callback.from_user.id,
        title="💎 Подписка на 7 дней",
        description="Доступ в приватный канал на 7 дней",
        payload="sub_7",
        provider_token="",
        currency="XTR",
        prices=prices
    )

@dp.callback_query(F.data == "buy_30")
async def buy30(callback):
    prices = [LabeledPrice(label="30 дней", amount=300)]

    await bot.send_invoice(
        callback.from_user.id,
        title="👑 Подписка на 30 дней",
        description="Доступ в приватный канал на 30 дней",
        payload="sub_30",
        provider_token="",
        currency="XTR",
        prices=prices
    )

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload

    days = 0

    if payload == "sub_1":
        days = 1
    elif payload == "sub_7":
        days = 7
    elif payload == "sub_30":
        days = 30

    expire = datetime.now() + timedelta(days=days)

    cursor.execute(
        "INSERT INTO users VALUES (?, ?)",
        (message.from_user.id, expire.strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.commit()

    link = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        member_limit=1
    )

    await message.answer(
        f"✅ Оплата прошла успешно!\n\n🔗 Ссылка:\n{link.invite_link}"
    )

async def check_subscriptions():
    while True:
        now = datetime.now()

        cursor.execute("SELECT user_id, end_date FROM users")
        users = cursor.fetchall()

        for user_id, end_date in users:
            end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

            if now > end_date:
                try:
                    await bot.ban_chat_member(CHANNEL_ID, user_id)
                    await bot.unban_chat_member(CHANNEL_ID, user_id)

                    await bot.send_message(
                        user_id,
                        "❌ Подписка закончилась."
                    )

                    cursor.execute(
                        "DELETE FROM users WHERE user_id=?",
                        (user_id,)
                    )

                    db.commit()

                except:
                    pass

        await asyncio.sleep(60)

async def main():
    asyncio.create_task(check_subscriptions())
    await dp.start_polling(bot)

asyncio.run(main())
