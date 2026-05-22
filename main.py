@dp.message(Command("start"))
async def start(message: Message):
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    # Обработка реферальной ссылки
    if referrer_id and referrer_id != message.from_user.id:
        cur.execute("SELECT subscription_end FROM users WHERE user_id = ?", (referrer_id,))
        result = cur.fetchone()
        if result and result[0]:
            new_end = (datetime.fromisoformat(result[0]) + timedelta(days=BONUS_DAYS)).isoformat()
            cur.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, referrer_id))
            conn.commit()
            try:
                await bot.send_message(referrer_id, "🎉 По вашей реферальной ссылке активировался новый пользователь!\n+1 день добавлен к вашей подписке!")
            except:
                pass

    text = """👋 <b>Добро пожаловать в Premium Ducks Bot!</b>

🦆 Здесь ты получаешь доступ к <b>закрытому каналу</b> с самыми редкими утками:
Rare • Epic • Legendary • Unique

🔥 <b>Что даёт подписка?</b>
• Мгновенные уведомления о новых редкостях
• Прямые ссылки
• Без рекламы и мусора

🎁 <b>Реферальная система</b>
Пригласи друга — получи +1 день бесплатно к своей подписке!

🆓 <b>Пробный доступ</b> — 2 дня (1 раз на аккаунт)

Выбери нужный вариант ниже 👇"""

    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")