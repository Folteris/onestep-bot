import os
import logging
import uvicorn
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from bot import get_bot, get_dispatcher
from database import engine, Base

# Настройки
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например, https://onestep-bot.onrender.com
PORT = int(os.getenv("PORT", 8000))
WEBHOOK_PATH = "/webhook"

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и FastAPI
bot = get_bot()
dp = get_dispatcher()
app = FastAPI()

# Webhook endpoint
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

# Startup
@app.on_event("startup")
async def on_startup():
    if not WEBHOOK_URL:
        logging.error("❌ WEBHOOK_URL не задан!")
    else:
        await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
        logging.info(f"✅ Webhook установлен: {WEBHOOK_URL}{WEBHOOK_PATH}")

    # Создание таблиц в базе данных
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info("✅ База данных инициализирована.")

# Shutdown
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    logging.info("🔌 Webhook удалён.")

# Запуск uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
