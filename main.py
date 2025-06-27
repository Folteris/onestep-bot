import os
import logging
from fastapi import FastAPI, Request
from aiogram import types, Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
import uvicorn

from bot import get_bot, get_dispatcher  # обязательно добавим эти функции в bot.py

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # например: https://onestep-bot.onrender.com
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", 8000))

bot = get_bot()
dp = get_dispatcher()
app = FastAPI()

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def startup():
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
    logging.info("Webhook установлен.")

@app.on_event("shutdown")
async def shutdown():
    await bot.delete_webhook()
    logging.info("Webhook удалён.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
