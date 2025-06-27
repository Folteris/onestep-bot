import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = '7606994315:AAGuq7yqLks531exYmD8zGEPc4A_Kh9AA3s'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

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

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message, state: FSMContext):
    if message.from_user.id in users:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔍 Найти собеседника")]],
            resize_keyboard=True
        )
        await message.answer("Ты уже регистрирован!\nНажми на кнопку ниже, чтобы найти кого-то 😉", reply_markup=kb)
    else:
        await Form.name.set()
        await message.answer("👋 Привет! Как тебя зовут?")

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await Form.next()
    await message.answer("Сколько тебе лет?")

@dp.message_handler(state=Form.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введи число.")
    await state.update_data(age=int(message.text))
    await Form.next()
    keyboard = InlineKeyboardMarkup()
    for country in COUNTRIES:
        keyboard.add(InlineKeyboardButton(text=country, callback_data=f"country_{country}"))
    await message.answer("Выбери страну:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('country_'), state=Form.country)
async def process_country(callback_query: types.CallbackQuery, state: FSMContext):
    country = callback_query.data.split('_')[1]
    await state.update_data(country=country)
    await Form.next()
    keyboard = InlineKeyboardMarkup()
    for city in CITIES[country]:
        keyboard.add(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
    await bot.send_message(callback_query.from_user.id, "Выбери город:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('city_'), state=Form.city)
async def process_city(callback_query: types.CallbackQuery, state: FSMContext):
    city = callback_query.data.split('_')[1]
    await state.update_data(city=city)
    await Form.next()
    keyboard = InlineKeyboardMarkup()
    for goal in GOALS:
        keyboard.add(InlineKeyboardButton(text=goal, callback_data=f"goal_{goal}"))
    await bot.send_message(callback_query.from_user.id, "Что ты сегодня ищешь?", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('goal_'), state=Form.goal)
async def process_goal(callback_query: types.CallbackQuery, state: FSMContext):
    goal = callback_query.data.split('_')[1]
    await state.update_data(goal=goal)
    await Form.next()
    await bot.send_message(callback_query.from_user.id, "Расскажи немного о себе")

@dp.message_handler(state=Form.bio)
async def process_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await Form.next()
    await message.answer("Отправь своё фото")

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data['photo'] = message.photo[-1].file_id
    users[message.from_user.id] = data
    await state.finish()

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("🔍 Найти собеседника")]],
        resize_keyboard=True
    )
    await message.answer("🎉 Анкета создана! Теперь ты можешь искать людей 👇", reply_markup=kb)

@dp.message_handler(commands='find')
@dp.message_handler(lambda message: message.text == "🔍 Найти собеседника")
async def find_by_button(message: types.Message):
    await find_match(message)

async def find_match(message: types.Message):
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

