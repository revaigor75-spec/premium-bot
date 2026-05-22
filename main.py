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
dp = Dispatcher()   # ← Вот здесь определяется dp

# ====================== БАЗА ДАННЫХ ======================
conn = sqlite3.connect('users.db')
cur = conn.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    subscription_end TEXT,
    trial_used INTEGER DEFAULT 0,
    referrer_id INTEGER
)''')
conn.commit()

# ====================== ФУНКЦИИ ======================
def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cur.fetchone()

def add_days(user_id, username, days, referrer_id=None):
    end_date = (datetime.now() + timedelta(days=days)).isoformat()
    cur.execute("""INSERT OR REPLACE INTO users 
                   (user_id, username, subscription_end, trial_used, referrer_id) 
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, username, end_date, 1 if days == TRIAL_DAYS else 0, referrer_id))
    conn.commit()

# ====================== КЛАВИАТУРА ======================
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🆓 Пробный доступ (2 дня)", callback_data="trial")
    builder.button(text="⭐ 1 день — 20 Stars", callback_data="buy_1")
    builder.button(text="⭐ 7 дней — 100 Stars", callback_data="buy_7")
    builder.button(text="⭐ 30 дней — 300 Stars", callback_data="buy_30")
    builder.button(text="🎁 Бонус (Рефералка)", callback_data="bonus")
    builder.button(text="🛠 Техподдержка", url="https://t.me/viksmuyk")
    builder.adjust(1)
    return builder.as_markup()

# ====================== СТАРТ ======================
@dp.message(Command("start"))
async def start(message: Message):
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    if referrer_id and referrer_id != message.from_user.id:
        cur.execute("SELECT subscription_end FROM users WHERE user_id = ?", (referrer_id,))
        result = cur.fetchone()
        if result and result[0]:
            new_end = (datetime.fromisoformat(result[0]) + timedelta(days=BONUS_DAYS)).isoformat()
            cur.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, referrer_id))
            conn.commit()
            try:
                await bot.send_message(referrer_id, "🎉 По вашей реферальной ссылке активировался новый пользователь!\n+1 день добавлен!")
            except:
                pass

    text = """👋 <b>Добро пожаловать в Premium Ducks Bot!</b>

🦆 Здесь ты получаешь доступ к <b>закрытому каналу</b> с самыми редкими утками:
Rare • Epic • Legendary • Unique

🔥 <b>Что даёт подписка?</b>
• Мгновенные уведомления о новых редкостях
• Прямые ссылки
• Без рекламы

🎁 <b>Реферальная система</b>
Пригласи друга — получи +1 день бесплатно!

🆓 Пробный доступ — 2 дня (1 раз)

Выбери вариант ниже 👇"""

    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# ====================== ПРОБНЫЙ ДОСТУП ======================
@dp.callback_query(F.data == "trial")
async def give_trial(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if user and user[3] == 1:
        await callback.answer("Вы уже использовали пробный период!", show_alert=True)
        return

    add_days(callback.from_user.id, callback.from_user.username, TRIAL_DAYS)
    
    link = await bot.create_chat_invite_link(CHANNEL_ID, member_limit=1, expire_date=int((datetime.now() + timedelta(days=3)).timestamp()))
    
    await callback.message.answer(
        f"✅ <b>Пробный доступ на {TRIAL_DAYS} дня активирован!</b>\n\n"
        f"🔗 Ваша ссылка: {link.invite_link}\n\n"
        "⚠️ Ссылка одноразовая.", 
        parse_mode="HTML"
    )
    await callback.answer()

# ====================== ОПЛАТА ======================
@dp.callback_query(F.data.startswith("buy_"))
async def process_payment(callback: CallbackQuery):
    data = callback.data
    if data == "buy_1":    amount, days = 20, 1;   title = "1 день доступа"
    elif data == "buy_7":  amount, days = 100, 7; title = "7 дней доступа"
    else:                  amount, days = 300, 30; title = "30 дней доступа"

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

# ====================== БОНУС ======================
@dp.callback_query(F.data == "bonus")
async def bonus_ref(callback: CallbackQuery):
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={callback.from_user.id}"
    await callback.message.answer(
        "🎁 <b>Твоя реферальная ссылка:</b>\n\n"
        f"{ref_link}\n\n"
        "Каждый, кто зайдёт по ней — даст тебе +1 день к подписке!",
        parse_mode="HTML"
    )
    await callback.answer()

# ====================== УСПЕШНАЯ ОПЛАТА ======================
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    days = int(message.successful_payment.invoice_payload.split("_")[1])
    add_days(message.from_user.id, message.from_user.username, days)
    
    link = await bot.create_chat_invite_link(CHANNEL_ID, member_limit=1)
    
    await message.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"Доступ активирован на <b>{days} дней</b>.\n\n"
        f"🔗 Ссылка: {link.invite_link}",
        parse_mode="HTML"
    )

# ====================== ЗАПУСК ======================
async def main():
    print("✅ Premium Ducks Bot успешно запущен!")
    await dp.start_polling(bot)

asyncio.run(main())
