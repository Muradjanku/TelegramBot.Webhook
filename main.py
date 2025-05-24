import os
from http import HTTPStatus
import aiohttp
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "7953800384:AAGUF3MW1H_zlT3gTOjvyUBX9bxMvNCO5l4"
WEBHOOK_DOMAIN = "https://telegram-bot-with-webhooks.up.railway.app/"  # O'zgartiring

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TelegramBot/1.0; +https://t.me/your_bot)"
}

app = FastAPI()

async def search_kitob_uz(query: str):
    url = f"https://www.kitob.uz/search?query={query.replace(' ', '+')}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()
            soup = BeautifulSoup(text, "html.parser")
            results = []
            for item in soup.select(".card-item"):
                title_tag = item.select_one(".card-title")
                link_tag = item.select_one("a")
                if title_tag and link_tag:
                    title = title_tag.text.strip()
                    link = "https://www.kitob.uz" + link_tag.get("href")
                    results.append(f"{title}\n{link}")
            return results

async def search_mykitob_uz(query: str):
    url = f"https://mykitob.uz/?s={query.replace(' ', '+')}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()
            soup = BeautifulSoup(text, "html.parser")
            results = []
            for post in soup.select(".post"):
                title_tag = post.select_one(".entry-title")
                link_tag = post.select_one("a")
                if title_tag and link_tag:
                    title = title_tag.text.strip()
                    link = link_tag.get("href")
                    results.append(f"{title}\n{link}")
            return results

async def send_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    await update.message.reply_text(f"📖 '{query}' kitobi uchun qidirilmoqda...")
    results_1 = await search_kitob_uz(query)
    results_2 = await search_mykitob_uz(query)
    results = results_1 + results_2
    if not results:
        await update.message.reply_text("Kechirasiz, bu kitob topilmadi.")
        return
    reply_text = "Topilgan kitoblar:\n\n" + "\n\n".join(results[:5])
    await update.message.reply_text(reply_text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 Kitob qidirish botiga xush kelibsiz!\n"
        "Istalgan kitob nomini yozing, men topishga harakat qilaman.\n"
        "/help - yordam"
    )
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Kitob nomini yozing yoki /search <kitob nomi> komandasi bilan qidiring.\n"
        "Misol: /search Otkan kunlar"
    )
    await update.message.reply_text(text)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        query = " ".join(context.args).strip()
        await send_search_results(update, context, query)
    else:
        await update.message.reply_text("Iltimos, qidiriladigan kitob nomini yozing.\nMisol: /search Otkan kunlar")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    await send_search_results(update, context, query)

app_telegram = Application.builder().token(TOKEN).build()

app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(CommandHandler("help", help_command))
app_telegram.add_handler(CommandHandler("search", search_command))
app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, app_telegram.bot)
    await app_telegram.process_update(update)
    return Response(status_code=HTTPStatus.OK)

@app.on_event("startup")
async def on_startup():
    await app_telegram.bot.set_webhook(WEBHOOK_DOMAIN)

@app.on_event("shutdown")
async def on_shutdown():
    await app_telegram.bot.delete_webhook()
