from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import os
import sqlite3
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003900818213        # ← твой канал
TRIAL_DAYS = 2

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====================== БАЗА ДАННЫХ ======================
conn = sqlite3.connect('users.db')
cur = conn.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    subscription_end TEXT,
    trial_used INTEGER DEFAULT 0
)''')
conn.commit()

# ====================== ФУНКЦИИ ======================
def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cur.fetchone()

def add_or_update_user(user_id, username, days):
    end_date = (datetime.now() + timedelta(days=days)).isoformat()
    cur.execute("""INSERT OR REPLACE INTO users 
                   (user_id, username, subscription_end, trial_used) 
                   VALUES (?, ?, ?, 
                   COALESCE((SELECT trial_used FROM users WHERE user_id = ?), 0))""",
                (user_id, username, end_date, user_id))
    conn.commit()

# ====================== КЛАВИАТУРА ======================
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ 1 день — 20 Stars", callback_data="buy_1")
    builder.button(text="⭐ 7 дней — 120 Stars", callback_data="buy_7")
    builder.button(text="⭐ 30 дней — 400 Stars", callback_data="buy_30")
    builder.button(text="🆓 Пробный доступ (2 дня)", callback_data="trial")
    builder.adjust(1)
    return builder.as_markup()

# ====================== КОМАНДЫ ======================
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в Premium Ducks Bot!\n\n"
        "Здесь ты можешь получить доступ к закрытому каналу с редкими утками.",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data == "trial")
async def give_trial(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if user and user[3] == 1:  # trial_used
        await callback.answer("Вы уже использовали пробный период!", show_alert=True)
        return

    add_or_update_user(callback.from_user.id, callback.from_user.username, TRIAL_DAYS)
    cur.execute("UPDATE users SET trial_used = 1 WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()

    link = await bot.create_chat_invite_link(CHANNEL_ID, member_limit=1, expire_date=int((datetime.now() + timedelta(days=TRIAL_DAYS+1)).timestamp()))
    
    await callback.message.answer(
        f"✅ Пробный доступ на {TRIAL_DAYS} дня активирован!\n\n"
        f"🔗 Ваша ссылка: {link.invite_link}\n\n"
        "Ссылка одноразовая. Не передавайте её другим."
    )
    await callback.answer()

# ====================== ОПЛАТА ======================
@dp.callback_query(F.data.startswith("buy_"))
async def process_payment(callback: CallbackQuery):
    data = callback.data
    if data == "buy_1":
        amount, days = 20, 1
        title = "1 день доступа"
    elif data == "buy_7":
        amount, days = 120, 7
        title = "7 дней доступа"
    else:
        amount, days = 400, 30
        title = "30 дней доступа"

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=f"Доступ к закрытому каналу на {days} дней",
        payload=f"premium_{days}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=amount)]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    days = int(payload.split("_")[1])
    
    add_or_update_user(message.from_user.id, message.from_user.username, days)
    
    link = await bot.create_chat_invite_link(CHANNEL_ID, member_limit=1)
    
    await message.answer(
        f"✅ Оплата прошла успешно!\n"
        f"Доступ активирован на {days} дней.\n\n"
        f"🔗 Ваша ссылка: {link.invite_link}"
    )

# ====================== ЗАПУСК ======================
async def main():
    print("Premium Bot запущен...")
    await dp.start_polling(bot)

asyncio.run(main())