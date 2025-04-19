import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import TELEGRAM_TOKEN, configure_logging
from handlers import register_all_handlers
from models.database import init_db  # Import the init_db function

# Настройка логирования
configure_logging()
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()


async def main():
    """Запуск бота"""
    # Initialize the database first
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")

    # Удаляем все обновления, которые могли накопиться
    await bot.delete_webhook(drop_pending_updates=True)

    # Регистрация всех обработчиков
    register_all_handlers(dp)

    # Запускаем бота в режиме long polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())