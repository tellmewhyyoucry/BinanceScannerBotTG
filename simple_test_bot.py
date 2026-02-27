import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler

# Загружаем переменные
load_dotenv()

TELEGRAM_TOKEN = os.getenv('8545214216:AAGRz-jmD-2989hx8LuP43Svse9AEC-v1HI')
ADMIN_CHAT_ID = os.getenv('1077455247')

async def start_command(update: Update, context):
    await update.message.reply_text("🤖 Бот работает! Сканер активирован.")

async def main():
    print("🔍 Проверка токена...")
    print(f"Токен: {'✅' if TELEGRAM_TOKEN else '❌'} {'Установлен' if TELEGRAM_TOKEN else 'Отсутствует'}")
    
    if not TELEGRAM_TOKEN:
        print("❌ ОШИБКА: Telegram токен не найден!")
        print("Проверьте файл .env")
        return
    
    try:
        # Создаем приложение
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler("start", start_command))
        
        print("✅ Токен валидный!")
        print("🚀 Запускаю бота...")
        
        # Проверяем соединение
        bot = Bot(token=TELEGRAM_TOKEN)
        me = await bot.get_me()
        print(f"🤖 Бот: @{me.username}")
        
        # Отправляем тестовое сообщение
        if ADMIN_CHAT_ID:
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text="✅ Бот успешно запущен и готов к работе!"
            )
            print("📨 Тестовое сообщение отправлено!")
        
        # Запускаем бота
        print("⏳ Ожидаю команды /start в Telegram...")
        await application.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("Возможные причины:")
        print("1. Неверный Telegram токен")
        print("2. Проблемы с интернет соединением")
        print("3. Токен заблокирован")

if __name__ == "__main__":
    asyncio.run(main())