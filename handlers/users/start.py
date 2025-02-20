import aiohttp
import aiosqlite
import asyncio
from datetime import datetime, time
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import CommandStart, Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils import executor
from data.config import ADMINS
from loader import bot, dp
from keyboards.reply.cities import cities

async def create_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                city TEXT,
                daily_notify INTEGER DEFAULT 0
            )
        """)
        await db.commit()

def daily_notify_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("\u2705 Ha, yuboring", callback_data="daily_yes"))
    keyboard.add(InlineKeyboardButton("\u274c Yo'q, kerak emas", callback_data="daily_no"))
    return keyboard

async def save_user_city(user_id, city):
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "INSERT INTO users (user_id, city) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET city = ?",
            (user_id, city, city),
        )
        await db.commit()

async def get_prayer_times(city):
    url = f"https://islomapi.uz/api/present/day?region={city}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
    
    hijri_month = data["hijri_date"]["month"]
    hijri_day = data["hijri_date"]["day"]
    bomdod = data["times"]["tong_saharlik"]
    sunrise = data["times"]["quyosh"]
    peshin = data["times"]["peshin"]
    asr = data["times"]["asr"]
    shom = data["times"]["shom_iftor"]
    xufton = data["times"]["hufton"]
    date = data["date"]
    kun = data["weekday"]
    hozirgi_vaqt = datetime.now().strftime('%H:%M')

    return f"""Namoz Vaqtlari:
    =========================
    \U0001F4CD 《 \U0001F307 {city} 》 vaqti bilan
    --------------------------------------------
    \U0001F30D  Hijri oy: - {hijri_month}
    \U0001F4C5  {hijri_month} oyining {hijri_day} - kuni

    \U0001F311  Tong - saharlik:  - {bomdod}
    \U0001F31E  Quyosh chiqishi: - {sunrise}

    \U0001F570  Bomdod:    -    {bomdod}
    \U0001F570  Peshin:      -    {peshin}
    \U0001F570  Asr:            -    {asr}
    \U0001F570  Shom:          -    {shom}
    \U0001F570  Xufton:    -    {xufton}

    \U0001F4C5 {date[:4]} - yil | Oyning {date[5:7]} - kuni | {kun} | Vaqt - {hozirgi_vaqt}
    """

@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    await message.answer(f"Salom, {message.from_user.full_name}!", reply_markup=cities)

@dp.message_handler(lambda message: message.text in ["Toshkent", "Samarqand", "Namangan", "Buxoro", "Andijan", "Jizzax"])
async def city_prayer_times(message: types.Message):
    city = message.text
    await save_user_city(message.from_user.id, city)
    prayer_times = await get_prayer_times(city)
    await message.answer(prayer_times, reply_markup=daily_notify_keyboard())

@dp.callback_query_handler(Text(startswith="daily_"))
async def set_daily_notify(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    daily_notify = 1 if callback_query.data == "daily_yes" else 0
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE users SET daily_notify = ? WHERE user_id = ?", (daily_notify, user_id))
        await db.commit()
    
    response_text = "✅ Har kuni namoz vaqtlari yuboriladi." if daily_notify else "❌ Namoz vaqtlari yuborilmaydi."
    await callback_query.message.answer(response_text)
    await callback_query.answer()

async def send_prayer_times():
    while True:
        now = datetime.now().time()
        if now.hour == 20 and now.minute == 0:
            async with aiosqlite.connect("database.db") as db:
                async with db.execute("SELECT user_id, city FROM users WHERE daily_notify = 1") as cursor:
                    users = await cursor.fetchall()

            for user_id, city in users:
                prayer_times = await get_prayer_times(city)
                await bot.send_message(user_id, prayer_times)
            await asyncio.sleep(60)  # 1 daqiqa kutish
        await asyncio.sleep(30)

async def on_startup(dp):
    await create_db()
    asyncio.create_task(send_prayer_times())
