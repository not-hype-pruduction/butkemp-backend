import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.enums.parse_mode import ParseMode
from yandex_cloud_ml_sdk import YCloudML
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токены доступа
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
YANDEX_GPT_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_GPT_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# История сообщений для контекста беседы
user_sessions = {}

# Создание клиента для работы с Яндекс ГПТ
sdk = YCloudML(
    folder_id=YANDEX_GPT_FOLDER_ID,
    auth=YANDEX_GPT_API_KEY
)
model = sdk.models.completions('yandexgpt-lite')
model.configure(
    temperature=0.6,
    max_tokens=1500
)

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start."""
    user_id = message.from_user.id
    user_sessions[user_id] = []

    await message.answer(
        "Привет! Я бот-психолог, готовый выслушать тебя и помочь. "
        "Расскажи мне, что тебя беспокоит?"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработка команды /help."""
    await message.answer(
        "Я бот-психолог, созданный для поддержки и помощи. "
        "Просто напиши мне о своих чувствах, проблемах или ситуациях, "
        "и я постараюсь помочь. Используй /reset чтобы начать разговор заново."
    )


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    """Сбросить историю диалога."""
    user_id = message.from_user.id
    user_sessions[user_id] = []
    await message.answer("История разговора сброшена. Начнем заново?")


def get_yandex_gpt_response(messages):
    """Получить ответ от Яндекс ГПТ с использованием SDK."""
    try:
        # Подготовка сообщений в формате для SDK
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'role': msg["role"],
                'text': msg["text"]
            })

        # Выполнение запроса к модели
        operation = model.run_deferred(formatted_messages)
        result = operation.wait()
        return result.text

    except Exception as e:
        logger.error(f"Ошибка при обращении к Яндекс ГПТ: {e}")
        return "Извините, у меня возникли проблемы с получением ответа. Попробуйте еще раз позже."


@dp.message()
async def process_message(message: types.Message):
    """Обработка входящих сообщений."""
    user_id = message.from_user.id
    user_message = message.text

    # Инициализируем сессию, если это первое сообщение
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Добавляем системное сообщение, если это первое сообщение
    if not user_sessions[user_id]:
        user_sessions[user_id].append({
            "role": "system",
            "text": "Ты психолог. Твоя задача - поддерживать диалог, проявлять эмпатию и давать психологические советы. Не упоминай, что ты ИИ или бот."
        })

    # Добавляем сообщение пользователя
    user_sessions[user_id].append({"role": "user", "text": user_message})

    # Ограничиваем историю сообщений (для экономии токенов)
    if len(user_sessions[user_id]) > 10:
        # Сохраняем системное сообщение и последние 9 сообщений
        user_sessions[user_id] = [user_sessions[user_id][0]] + user_sessions[user_id][-9:]

    # Отправляем "печатает..." статус
    await bot.send_chat_action(chat_id=user_id, action="typing")

    # Получаем ответ от Яндекс ГПТ
    response = get_yandex_gpt_response(user_sessions[user_id])

    # Добавляем ответ ассистента в историю
    user_sessions[user_id].append({"role": "assistant", "text": response})

    # Отправляем ответ пользователю
    await message.answer(response)


async def main():
    """Запуск бота."""
    # Удаляем все обновления, которые могли накопиться
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем бота в режиме long polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())