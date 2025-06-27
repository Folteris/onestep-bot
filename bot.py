import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, ContentType
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

API_TOKEN = '7606994315:AAGuq7yqLks531exYmD8zGEPc4A_Kh9AA3s'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Form(StatesGroup):
    name = State()
    age = State()
    country = State()
    city = State()
    goal = State()
    bio = State()
    photo = State()

users = {}

COUNTRIES = ['Украина', 'Польша']
CITIES = {
    'Украина': ['Киев', 'Львов', 'Харьков'],
    'Польша': ['Варшава', 'Краков', 'Гданьск']
}
GOALS = ['Общение', 'Дружба', 'Отношения']

@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    if message.from_user.id in users:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔍 Найти собеседника")]],
            resize_keyboard=True
        )
        await message.answer("Ты уже зарегистрирован!\nНажми на кнопку ниже, чтобы найти кого-то 😉", reply_markup=kb)
    else:
        await state.set_state(Form.name)
        await message.answer("👋 Привет! Как тебя зовут?")

@dp.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.age)
    await message.answer("Сколько тебе лет?")

@dp.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введи число.")
    await state.update_data(age=int(message.text))
    await state.set_state(Form.country)
    keyboard = InlineKeyboardMarkup()
    for country in COUNTRIES:
        keyboard.add(InlineKeyboardButton(text=country, callback_data=f"country_{country}"))
    await message.answer("Выбери страну:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("country_"))
async def process_country(callback_query: CallbackQuery, state: FSMContext):
    country = callback_query.data.split('_')[1]
    await state.update_data(country=country)
    await state.set_state(Form.city)
    keyboard = InlineKeyboardMarkup()
    for city in CITIES[country]:
        keyboard.add(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
    await bot.send_message(callback_query.from_user.id, "Выбери город:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("city_"))
async def process_city(callback_query: CallbackQuery, state: FSMContext):
    city = callback_query.data.split('_')[1]
    await state.update_data(city=city)
    await state.set_state(Form.goal)
    keyboard = InlineKeyboardMarkup()
    for goal in GOALS:
        keyboard.add(InlineKeyboardButton(text=goal, callback_data=f"goal_{goal}"))
    await bot.send_message(callback_query.from_user.id, "Что ты сегодня ищешь?", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("goal_"))
async def process_goal(callback_query: CallbackQuery, state: FSMContext):
    goal = callback_query.data.split('_')[1]
    await state.update_data(goal=goal)
    await state.set_state(Form.bio)
    await bot.send_message(callback_query.from_user.id, "Расскажи немного о себе")

@dp.message(Form.bio)
async def process_bio(message: Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await state.set_state(Form.photo)
    await message.answer("Отправь своё фото")

@dp.message(Form.photo, F.content_type == ContentType.PHOTO)
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    data['photo'] = message.photo[-1].file_id
    users[message.from_user.id] = data
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("🔍 Найти собеседника")]],
        resize_keyboard=True
    )
    await message.answer("🎉 Анкета создана! Теперь ты можешь искать людей 👇", reply_markup=kb)

@dp.message(F.text == "/find")
@dp.message(F.text == "🔍 Найти собеседника")
async def find_by_button(message: Message):
    await find_match(message)

async def find_match(message: Message):
    user = users.get(message.from_user.id)
    if not user:
        return await message.answer("Сначала заполни анкету командой /start")
    for user_id, data in users.items():
        if user_id != message.from_user.id and data['city'] == user['city'] and data['goal'] == user['goal']:
            text = f"👤 {data['name']}, {data['age']} лет\n📍 {data['city']}, {data['country']}\n🌟 Цель: {data['goal']}\n📝 {data['bio']}"
            await bot.send_photo(message.chat.id, data['photo'], caption=text)
            return
    await message.answer("Пока нет подходящих пользователей онлайн. Попробуй позже!")

def get_bot():
    return bot

def get_dispatcher():
    return dp
