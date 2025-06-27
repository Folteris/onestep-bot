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
        keyboard.add(InlineKeyboardButton(text=city
