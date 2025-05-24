import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
import httpx

TELEGRAM_BOT_TOKEN = "7850276923:AAHtlpa-L0MQgf8qpFWt1MJFWmT1WooRf0A"
WEBHOOK_DOMAIN = "https://muradali.railway.internal"  # https kerak

bot_builder = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .updater(None)
    .build()
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    webhook_url = WEBHOOK_DOMAIN if WEBHOOK_DOMAIN.endswith('/') else WEBHOOK_DOMAIN + '/'
    await bot_builder.bot.setWebhook(url=webhook_url)
    async with bot_builder:
        await bot_builder.start()
        yield
        await bot_builder.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/")
async def process_update(request: Request):
    message = await request.json()
    update = Update.de_json(data=message, bot=bot_builder.bot)
    await bot_builder.process_update(update)
    return Response(status_code=HTTPStatus.OK)

async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! So‘z yuboring, men Wikipedia'dan uning ma'nosini topib beraman."
    )

async def wiki_meaning(word: str) -> str:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{word}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            if "extract" in data:
                return data["extract"]
            else:
                return "Kechirasiz, bu so‘z uchun qisqacha ma’lumot topilmadi."
        elif response.status_code == 404:
            return "Kechirasiz, bunday maqola topilmadi."
        else:
            return "Wikipedia bilan bog‘liq muammo yuz berdi."

async def handle_message(update: Update, _: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    meaning = await wiki_meaning(text)
    await update.message.reply_text(meaning)

bot_builder.add_handler(CommandHandler("start", start))
bot_builder.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
