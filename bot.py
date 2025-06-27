
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = '7606994315:AAGuq7yqLks531exYmD8zGEPc4A_Kh9AA3s'

# Enable logging
logging.basicConfig(level=logging.INFO)

# Bot and Dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# FSM states for registration
class Form(StatesGroup):
    name = State()
    age = State()
    city = State()
    photo = State()
    bio = State()

# Simple in-memory storage (replace with DB later)
users = {}

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await Form.name.set()
    await message.answer("👋 Привет! Давай создадим твою анкету. Как тебя зовут?")

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
    await message.answer("Из какого ты города?")

@dp.message_handler(state=Form.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await Form.next()
    await message.answer("Отправь своё фото")

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.photo)
async def process_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await Form.next()
    await message.answer("Расскажи немного о себе")

@dp.message_handler(state=Form.bio)
async def process_bio(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data['bio'] = message.text
    users[message.from_user.id] = data
    await message.answer("🎉 Твоя анкета сохранена! Скоро ты сможешь увидеть других пользователей.")
    await state.finish()

@dp.message_handler(commands='show')
async def show_random_profile(message: types.Message):
    for user_id, data in users.items():
        if user_id != message.from_user.id:
            text = f"👤 {data['name']}, {data['age']} лет\n📍 {data['city']}\n📝 {data['bio']}"
            await bot.send_photo(message.chat.id, data['photo'], caption=text)
            return
    await message.answer("Пока нет других анкет. Попробуй позже!")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
