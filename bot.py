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

# Параметры подключения к Redis из переменных окружения
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Инициализация Redis-клиента
redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
)

# Хранилище состояний FSM в Redis
storage = RedisStorage(redis=redis_client)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=storage)

# Списки стран, городов и целей
COUNTRIES = ['Украина', 'Польша']
CITIES = {
    'Украина': ['Киев', 'Львов', 'Харьков', 'Одесса', 'Днепр', 'Запорожье', 'Чернигов', 'Ивано-Франковск', 'Тернополь'],
    'Польша': ['Варшава', 'Краков', 'Гданьск']
}
GOALS = ['Общение', 'Дружба', 'Отношения']

# Определение состояний формы регистрации
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
    # Очищаем состояние на случай повторного /start
    await state.clear()
    # Проверяем, зарегистрирован ли пользователь в базе данных
    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalars().first()
        if user:
            # Пользователь уже есть в базе – предлагаем начать поиск собеседника
            kb = ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add(KeyboardButton(text="🔍 Найти собеседника"))
            await message.answer("Ты уже зарегистрирован. Нажми кнопку ниже, чтобы начать поиск!", reply_markup=kb)
            return
    # Если пользователя нет, начинаем регистрацию: спрашиваем имя
    await message.answer("👋 Привет! Как тебя зовут?")
    await state.set_state(Form.name)

@dp.message(Form.name)
async def get_name(message: types.Message, state: FSMContext):
    # Сохраняем имя и переходим к вопросу о возрасте
    await state.update_data(name=message.text)
    await state.set_state(Form.age)
    await message.answer("Сколько тебе лет?")

@dp.message(Form.age)
async def get_age(message: types.Message, state: FSMContext):
    # Возраст должен быть числом
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введи число.")
    await state.update_data(age=int(message.text))
    await state.set_state(Form.country)
    # Предлагаем выбрать страну через inline-кнопки
    keyboard = InlineKeyboardMarkup()
    for country in COUNTRIES:
        keyboard.add(InlineKeyboardButton(text=country, callback_data=f"country_{country}"))
    await message.answer("Выбери страну:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("country_"))
async def get_country(callback: types.CallbackQuery, state: FSMContext):
    # Получаем выбранную страну из callback_data
    country = callback.data.split("_", 1)[1]
    await state.update_data(country=country)
    await state.set_state(Form.city)
    # Формируем клавиатуру городов для выбранной страны
    keyboard = InlineKeyboardMarkup()
    for city in CITIES.get(country, []):
        keyboard.add(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
    # Редактируем предыдущее сообщение, предлагая выбрать город
    await callback.message.edit_text("Выбери город:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("city_"))
async def get_city(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.split("_", 1)[1]
    await state.update_data(city=city)
    await state.set_state(Form.goal)
    # Формируем клавиатуру целей знакомства
    keyboard = InlineKeyboardMarkup()
    for goal in GOALS:
        keyboard.add(InlineKeyboardButton(text=goal, callback_data=f"goal_{goal}"))
    # Редактируем сообщение, предлагая выбрать цель общения
    await callback.message.edit_text("Что ты сегодня ищешь?", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("goal_"))
async def get_goal(callback: types.CallbackQuery, state: FSMContext):
    goal = callback.data.split("_", 1)[1]
    await state.update_data(goal=goal)
    await state.set_state(Form.bio)
    # Убираем клавиатуру и просим рассказать о себе
    await callback.message.edit_text("Расскажи немного о себе:")
    await callback.answer()

@dp.message(Form.bio)
async def get_bio(message: types.Message, state: FSMContext):
    # Сохраняем биографию и переходим к этапу фото
    await state.update_data(bio=message.text)
    await state.set_state(Form.photo)
    await message.answer("Отправь своё фото")

@dp.message(Form.photo, F.photo)
async def get_photo(message: types.Message, state: FSMContext):
    # Получаем сохранённые данные анкеты из FSM
    data = await state.get_data()
    # Сохраняем или обновляем профиль пользователя в базе данных
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
        # Сохраняем file_id последней (самой крупной) отправленной фотографии
        user.photo = message.photo[-1].file_id
        session.add(user)
        await session.commit()
    # Очищаем состояние и подтверждаем сохранение анкеты
    await state.clear()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(text="🔍 Найти собеседника"))
    await message.answer("🎉 Анкета сохранена! Теперь ты можешь искать людей.", reply_markup=kb)

@dp.message(F.text == "🔍 Найти собеседника")
async def find_match(message: types.Message):
    async with get_session() as session:
        # Получаем текущего пользователя
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        me = result.scalars().first()
        if not me:
            return await message.answer("Для начала пройди регистрацию через /start.")
        # Ищем любого другого пользователя с тем же городом и целью
        match_query = await session.execute(
            select(User).where(
                User.city == me.city,
                User.goal == me.goal,
                User.telegram_id != me.telegram_id
            )
        )
        match = match_query.scalars().first()
        if not match:
            return await message.answer("Сейчас нет подходящих собеседников. Попробуй позже.")
        # Формируем сообщение с информацией о найденном пользователе
        text = (
            f"👤 {match.name}, {match.age} лет\n"
            f"📍 {match.city}, {match.country}\n"
            f"🌟 Цель: {match.goal}\n"
            f"📝 {match.bio}"
        )
        # Отправляем анкету найденного пользователя (фото + подпись)
        await bot.send_photo(chat_id=message.chat.id, photo=match.photo, caption=text)

# Если файл запущен напрямую, запускаем бота (long polling)
if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
