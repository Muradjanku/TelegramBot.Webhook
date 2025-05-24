import os
from contextlib import asynccontextmanager
from http import HTTPStatus
import aiohttp
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Response
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from mini_telegram import Bot, Dispatcher, types

# Token va webhook domeni
TOKEN = "7953800384:AAGUF3MW1H_zlT3gTOjvyUBX9bxMvNCO5l4"
WEBHOOK_DOMAIN = "https://telegram-bot-with-webhooks.up.railway.app/"  # O'zingizning domeningiz bilan almashtiring

# Bot va dispatcher yaratish
bot_builder = (
    Application.builder()
    .token(TOKEN)
    .updater(None)
    .build()
)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TelegramBot/1.0; +https://t.me/your_bot)"
}

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot_builder.bot.setWebhook(url=WEBHOOK_DOMAIN)
    async with bot_builder:
        await bot_builder.start()
        yield
        await bot_builder.stop()

app.router.lifespan_context = lifespan

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

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    text = (
        "📚 Kitob qidirish botiga xush kelibsiz!\n"
        "Istalgan kitob nomini yozing, men topishga harakat qilaman.\n"
        "/help - yordam"
    )
    await message.answer(text)

@dp.message_handler(commands=["help"])
async def help_handler(message: types.Message):
    text = (
        "Kitob nomini yozing yoki /search <kitob nomi> komandasi bilan qidiring.\n"
        "Misol: /search Otkan kunlar"
    )
    await message.answer(text)

@dp.message_handler(commands=["search"])
async def search_command_handler(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Iltimos, qidiriladigan kitob nomini yozing.\nMisol: /search Otkan kunlar")
        return
    query = args[1].strip()
    await send_search_results(message, query)

@dp.message_handler()
async def text_handler(message: types.Message):
    query = message.text.strip()
    await send_search_results(message, query)

async def send_search_results(message: types.Message, query: str):
    await message.answer(f"📖 '{query}' kitobi uchun qidirilmoqda...")
    results_1 = await search_kitob_uz(query)
    results_2 = await search_mykitob_uz(query)
    results = results_1 + results_2
    if not results:
        await message.answer("Kechirasiz, bu kitob topilmadi.")
        return
    reply_text = "Topilgan kitoblar:\n\n" + "\n\n".join(results[:5])
    await message.answer(reply_text)

@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return Response(status_code=HTTPStatus.OK)

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=WEBHOOK_DOMAIN)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

bot_builder.add_handler(CommandHandler(command="start", callback=start_handler))
bot_builder.add_handler(CommandHandler(command="help", callback=help_handler))
bot_builder.add_handler(CommandHandler(command="search", callback=search_command_handler))
bot_builder.add_handler(MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=text_handler))
