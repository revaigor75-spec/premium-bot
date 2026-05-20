import asyncio
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

TOKEN = "8620057655:AAG1oMogyI46UKw7LQ4_yp2pHAEKwCTHc_w"

GROUP_ID = -1003993795823
SUPPORT_USERNAME = "@viksmuyk"

from aiogram.client.default import DefaultBotProperties

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)
dp = Dispatcher()

db = sqlite3.connect("users.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    access_until TEXT,
    trial_used INTEGER DEFAULT 0
)
""")
db.commit()


def keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 Пробный доступ",
                    callback_data="trial"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ 1 день — 20 Stars",
                    callback_data="buy_1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ 7 дней — 100 Stars",
                    callback_data="buy_7"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ 30 дней — 300 Stars",
                    callback_data="buy_30"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛠 Техподдержка",
                    callback_data="support"
                )
            ],
        ]
    )


@dp.message(CommandStart())
async def start(message: Message):
    text = (
        "🦆 <b>Добро пожаловать в DUCK x MY x DUCK</b>\n\n"
        "Здесь открывается доступ только "
        "к премиум уткам 👀\n\n"
        "❌ Никаких Common\n"
        "❌ Никаких Uncommon\n\n"
        "Только редкие и ценные утки.\n\n"
        "🎁 Новым пользователям доступен "
        "пробный период на 2 дня."
    )

    await message.answer(
        text,
        reply_markup=keyboard()
    )


@dp.callback_query(F.data == "trial")
async def trial(callback: CallbackQuery):
    user_id = callback.from_user.id

    cursor.execute(
        "SELECT trial_used FROM users WHERE user_id=?",
        (user_id,)
    )

    user = cursor.fetchone()

    if user and user[0] == 1:
        await callback.message.answer(
            "❌ Ты уже использовал пробный доступ."
        )
        return

    expire = datetime.now() + timedelta(days=2)

    if user:
        cursor.execute(
            """
            UPDATE users
            SET access_until=?, trial_used=1
            WHERE user_id=?
            """,
            (
                expire.isoformat(),
                user_id
            )
        )
    else:
        cursor.execute(
            """
            INSERT INTO users
            (user_id, access_until, trial_used)
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                expire.isoformat(),
                1
            )
        )

    db.commit()

    invite = await bot.create_chat_invite_link(
        chat_id=GROUP_ID,
        member_limit=1,
        expire_date=datetime.now() + timedelta(minutes=30)
    )

    await callback.message.answer(
        "✅ Пробный доступ активирован!\n\n"
        "Ссылка действует 30 минут "
        "и только на 1 вход.\n\n"
        f"{invite.invite_link}"
    )


@dp.callback_query(F.data == "buy_1")
async def buy1(callback: CallbackQuery):
    await callback.message.answer(
        "⭐ Оплата 1 дня подписки\n\n"
        "Стоимость: 20 Telegram Stars\n\n"
        "После подключения оплаты Telegram "
        "здесь будет настоящая покупка."
    )


@dp.callback_query(F.data == "buy_7")
async def buy7(callback: CallbackQuery):
    await callback.message.answer(
        "⭐ Оплата 7 дней подписки\n\n"
        "Стоимость: 100 Telegram Stars"
    )


@dp.callback_query(F.data == "buy_30")
async def buy30(callback: CallbackQuery):
    await callback.message.answer(
        "⭐ Оплата 30 дней подписки\n\n"
        "Стоимость: 300 Telegram Stars"
    )


@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    text = (
        "🛠 <b>Техподдержка</b>\n\n"
        f"❓ Проблемы с оплатой → {SUPPORT_USERNAME}\n\n"
        f"❓ Потеряли доступ к группе → {SUPPORT_USERNAME}\n\n"
        f"❓ Хотите длительный пакет → {SUPPORT_USERNAME}\n\n"
        f"❓ Как получить бонус "
        f"за приглашение друга → {SUPPORT_USERNAME}"
    )

    await callback.message.answer(text)


async def checker():
    while True:
        cursor.execute(
            "SELECT user_id, access_until FROM users"
        )

        users = cursor.fetchall()

        for user_id, access_until in users:
            if not access_until:
                continue

            expire = datetime.fromisoformat(access_until)

            if datetime.now() >= expire:
                try:
                    await bot.ban_chat_member(
                        GROUP_ID,
                        user_id
                    )

                    await bot.unban_chat_member(
                        GROUP_ID,
                        user_id
                    )

                    await bot.send_message(
                        user_id,
                        "⛔ Ваша подписка закончилась.\n\n"
                        "Чтобы снова получить доступ "
                        "к премиум уткам — "
                        "оформите подписку."
                    )

                except:
                    pass

                cursor.execute(
                    """
                    UPDATE users
                    SET access_until=NULL
                    WHERE user_id=?
                    """,
                    (user_id,)
                )

                db.commit()

        await asyncio.sleep(60)


async def main():
    asyncio.create_task(checker())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
