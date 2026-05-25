from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, LabeledPrice
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import os
import sqlite3
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_ID = -1003900818213
TRIAL_DAYS = 2
BONUS_DAYS = 1

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====================== БАЗА ДАННЫХ ======================

conn = sqlite3.connect("users.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    subscription_end TEXT,
    trial_used INTEGER DEFAULT 0,
    referrer_id INTEGER
)
""")

conn.commit()

# ====================== ФУНКЦИИ ======================

def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cur.fetchone()


def add_days(user_id, username, days, referrer_id=None):

    cur.execute(
        "SELECT subscription_end, trial_used, referrer_id FROM users WHERE user_id = ?",
        (user_id,)
    )

    existing = cur.fetchone()

    if existing:

        current_end = existing[0]
        trial_used = existing[1]
        old_referrer = existing[2]

        # продление подписки
        if current_end:

            current_end_date = datetime.fromisoformat(current_end)

            if current_end_date > datetime.now():
                new_end = current_end_date + timedelta(days=days)
            else:
                new_end = datetime.now() + timedelta(days=days)

        else:
            new_end = datetime.now() + timedelta(days=days)

        # trial не сбрасывается
        if days == TRIAL_DAYS:
            trial_used = 1

        cur.execute("""
            UPDATE users
            SET username = ?,
                subscription_end = ?,
                trial_used = ?,
                referrer_id = ?
            WHERE user_id = ?
        """, (
            username,
            new_end.isoformat(),
            trial_used,
            old_referrer if old_referrer else referrer_id,
            user_id
        ))

    else:

        end_date = datetime.now() + timedelta(days=days)

        cur.execute("""
            INSERT INTO users (
                user_id,
                username,
                subscription_end,
                trial_used,
                referrer_id
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            username,
            end_date.isoformat(),
            1 if days == TRIAL_DAYS else 0,
            referrer_id
        ))

    conn.commit()

# ====================== КЛАВИАТУРА ======================

def get_main_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🆓 Пробный доступ (2 дня)",
        callback_data="trial"
    )

    builder.button(
        text="⭐ 1 день — 20 Stars",
        callback_data="buy_1"
    )

    builder.button(
        text="⭐ 7 дней — 100 Stars",
        callback_data="buy_7"
    )

    builder.button(
        text="⭐ 30 дней — 300 Stars",
        callback_data="buy_30"
    )

    builder.button(
        text="🎁 Бонус (Рефералка)",
        callback_data="bonus"
    )

    builder.button(
        text="🛠 Техподдержка",
        url="https://t.me/viksmuyk"
    )

    builder.adjust(1)

    return builder.as_markup()

# ====================== СТАРТ ======================

@dp.message(Command("start"))
async def start(message: Message):

    args = message.text.split()

    referrer_id = (
        int(args[1])
        if len(args) > 1 and args[1].isdigit()
        else None
    )

    # бонус по рефералке
    if referrer_id and referrer_id != message.from_user.id:

        cur.execute(
            "SELECT subscription_end FROM users WHERE user_id = ?",
            (referrer_id,)
        )

        result = cur.fetchone()

        if result and result[0]:

            new_end = (
                datetime.fromisoformat(result[0])
                + timedelta(days=BONUS_DAYS)
            ).isoformat()

            cur.execute(
                "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                (new_end, referrer_id)
            )

            conn.commit()

            try:
                await bot.send_message(
                    referrer_id,
                    "🎉 По вашей реферальной ссылке пришёл новый пользователь!\n\n+1 день добавлен!"
                )
            except:
                pass

    text = """
👋 <b>Добро пожаловать в Premium Ducks Bot!</b>

🦆 Здесь ты получаешь доступ к закрытому каналу с самыми редкими утками:
Rare • Epic • Legendary • Unique

🔥 <b>Что даёт подписка?</b>
• Мгновенные уведомления
• Прямые ссылки
• Без рекламы

🎁 <b>Реферальная система</b>
Пригласи друга — получи +1 день бесплатно!

🆓 Пробный доступ — 2 дня (1 раз)

Выбери вариант ниже 👇
"""

    await message.answer(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

# ====================== ПРОБНЫЙ ДОСТУП ======================

@dp.callback_query(F.data == "trial")
async def give_trial(callback: CallbackQuery):

    user = get_user(callback.from_user.id)

    # если trial уже использован
    if user and user[3] == 1:

        await callback.answer(
            "❌ Вы уже использовали пробный доступ!",
            show_alert=True
        )

        return

    # выдаём доступ
    add_days(
        callback.from_user.id,
        callback.from_user.username,
        TRIAL_DAYS
    )

    link = await bot.create_chat_invite_link(
        CHANNEL_ID,
        member_limit=1,
        expire_date=int(
            (datetime.now() + timedelta(days=3)).timestamp()
        )
    )

    await callback.message.answer(
        f"""
✅ <b>Пробный доступ активирован!</b>

⏳ Срок: {TRIAL_DAYS} дня

🔗 Ссылка:
{link.invite_link}

⚠️ Ссылка одноразовая.
""",
        parse_mode="HTML"
    )

    await callback.answer()

# ====================== ПОКУПКА ======================

@dp.callback_query(F.data.startswith("buy_"))
async def process_payment(callback: CallbackQuery):

    data = callback.data

    if data == "buy_1":
        amount = 20
        days = 1
        title = "1 день доступа"

    elif data == "buy_7":
        amount = 100
        days = 7
        title = "7 дней доступа"

    else:
        amount = 300
        days = 30
        title = "30 дней доступа"

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=f"Доступ на {days} дней",
        payload=f"premium_{days}",
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=title,
                amount=amount
            )
        ]
    )

    await callback.answer()

# ====================== РЕФЕРАЛКА ======================

@dp.callback_query(F.data == "bonus")
async def bonus_ref(callback: CallbackQuery):

    bot_info = await bot.get_me()

    ref_link = (
        f"https://t.me/{bot_info.username}"
        f"?start={callback.from_user.id}"
    )

    await callback.message.answer(
        f"""
🎁 <b>Твоя реферальная ссылка:</b>

{ref_link}

За каждого пользователя:
+1 день подписки
""",
        parse_mode="HTML"
    )

    await callback.answer()

# ====================== ОПЛАТА УСПЕШНА ======================

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query):

    await bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True
    )

@dp.message(F.successful_payment)
async def successful_payment(message: Message):

    days = int(
        message.successful_payment.invoice_payload.split("_")[1]
    )

    add_days(
        message.from_user.id,
        message.from_user.username,
        days
    )

    link = await bot.create_chat_invite_link(
        CHANNEL_ID,
        member_limit=1
    )

    await message.answer(
        f"""
✅ <b>Оплата прошла успешно!</b>

⏳ Доступ активирован на {days} дней

🔗 Ссылка:
{link.invite_link}
""",
        parse_mode="HTML"
    )

# ====================== ЗАПУСК ======================

async def main():

    print("✅ Premium Ducks Bot успешно запущен!")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
