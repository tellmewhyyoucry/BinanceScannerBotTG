import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Простейший бот для теста
TELEGRAM_TOKEN = "8545214216:AAGRz-jmD-2989hx8LuP43Svse9AEC-v1HI"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает!")

async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    logger.info("Запускаю простого бота...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())