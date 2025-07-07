import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy import select
from database import User, get_session

logging.basicConfig(level=logging.INFO)

# Настройки Redis из переменных окружения
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Создаём Redis клиент
redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
)

# Создаём storage для FSM на базе Redis
storage = RedisStorage(redis=redis_client)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=storage)

COUNTRIES = ['Украина', 'Польша']
CITIES = {
    'Украина': ['Киев', 'Львов', 'Харьков', 'Одесса', 'Днепр', 'Запорожье', 'Чернигов', 'Ивано-Франковск', 'Тернополь'],
    'Польша': ['Варшава', 'Краков', 'Гданьск']
}
GOALS = ['Общение', 'Дружба', 'Отношения']

class Form(StatesGroup):
    name = State()
    age = State()
    country = State()
    city = State()
    goal = State()
    bio = State()
    photo = State()

@dp.message(F.text == "/start")
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalars().first()
        if user:
            kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔍 Найти собеседника")]], resize_keyboard=True)
            await message.answer("Ты уже зарегистрирован. Нажми кнопку ниже, чтобы начать поиск!", reply_markup=kb)
            return
    await message.answer("👋 Привет! Как тебя зовут?")
    await state.set_state(Form.name)

@dp.message(Form.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.age)
    await message.answer("Сколько тебе лет?")

@dp.message(Form.age)
async def get_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Введи число.")
    await state.update_data(age=int(message.text))

    await state.set_state(Form.country)  # Переключаем состояние _до_ отправки сообщения

    keyboard = InlineKeyboardMarkup(row_width=1)
    for country in COUNTRIES:
        keyboard.add(InlineKeyboardButton(text=country, callback_data=f"country_{country}"))

    await message.answer("Выбери страну:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("country_"))
async def get_country(callback: types.CallbackQuery, state: FSMContext):
    country = callback.data.split("_", 1)[1]
    await state.update_data(country=country)

    keyboard = InlineKeyboardMarkup(row_width=1)
    for city in CITIES.get(country, []):
        keyboard.add(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))

    await state.set_state(Form.city)
    await callback.message.edit_text("Выбери город:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("city_"))
async def get_city(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.split("_", 1)[1]
    await state.update_data(city=city)

    keyboard = InlineKeyboardMarkup(row_width=1)
    for goal in GOALS:
        keyboard.add(InlineKeyboardButton(text=goal, callback_data=f"goal_{goal}"))

    await state.set_state(Form.goal)
    await callback.message.edit_text("Что ты сегодня ищешь?", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("goal_"))
async def get_goal(callback: types.CallbackQuery, state: FSMContext):
    goal = callback.data.split("_", 1)[1]
    await state.update_data(goal=goal)
    await state.set_state(Form.bio)
    await callback.message.edit_text("Расскажи немного о себе")
    await callback.answer()

@dp.message(Form.bio)
async def get_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await state.set_state(Form.photo)
    await message.answer("Отправь своё фото")

@dp.message(Form.photo, F.photo)
async def get_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalars().first()
        if not user:
            user = User(telegram_id=message.from_user.id)
        user.name = data['name']
        user.age = data['age']
        user.country = data['country']
        user.city = data['city']
        user.goal = data['goal']
        user.bio = data['bio']
        user.photo = message.photo[-1].file_id
        session.add(user)
        await session.commit()

    await state.clear()
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔍 Найти собеседника")]], resize_keyboard=True)
    await message.answer("🎉 Анкета сохранена! Теперь можешь искать людей.", reply_markup=kb)

@dp.message(F.text == "🔍 Найти собеседника")
async def find_match(message: types.Message):
    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        me = result.scalars().first()
        if not me:
            return await message.answer("Сначала зарегистрируйся через /start")

        match_query = await session.execute(
            select(User).where(
                User.city == me.city,
                User.goal == me.goal,
                User.telegram_id != me.telegram_id
            )
        )
        match = match_query.scalars().first()
        if not match:
            return await message.answer("Нет подходящих собеседников сейчас. Попробуй позже.")

        text = (
            f"\U0001F464 {match.name}, {match.age} лет\n"
            f"\U0001F4CD {match.city}, {match.country}\n"
            f"\U0001F31F Цель: {match.goal}\n"
            f"\U0001F4DD {match.bio}"
        )
        await bot.send_photo(message.chat.id, match.photo, caption=text)

def get_bot():
    return bot

def get_dispatcher():
    return dp
