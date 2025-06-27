import os
import logging
import uvicorn
from fastapi import FastAPI
from aiogram.types import Update
from bot import get_bot, get_dispatcher  # Импорт из bot.py

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))

app = FastAPI()
bot = get_bot()
dp = get_dispatcher()

@app.post(WEBHOOK_PATH)
async def webhook(update: dict):
    telegram_update = Update.model_validate(update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
