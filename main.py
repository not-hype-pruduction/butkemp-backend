import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from yandex_cloud_ml_sdk import llm  # Импорт SDK для работы с Яндекс ГПТ

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токены доступа (в реальном приложении рекомендуется хранить в .env файле)
TELEGRAM_TOKEN = "ВАШ_ТЕЛЕГРАМ_ТОКЕН"
YANDEX_GPT_API_KEY = "ВАШ_ЯНДЕКС_GPT_API_KEY"
YANDEX_GPT_FOLDER_ID = "ВАШ_FOLDER_ID"  # ID каталога в Яндекс Облаке

# История сообщений для контекста беседы
user_sessions = {}

# Создание клиента для работы с Яндекс ГПТ
llm_client = llm.LLMClient(api_key=YANDEX_GPT_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start."""
    user_id = update.effective_user.id
    user_sessions[user_id] = []

    await update.message.reply_text(
        "Привет! Я бот-психолог, готовый выслушать тебя и помочь. "
        "Расскажи мне, что тебя беспокоит?"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help."""
    await update.message.reply_text(
        "Я бот-психолог, созданный для поддержки и помощи. "
        "Просто напиши мне о своих чувствах, проблемах или ситуациях, "
        "и я постараюсь помочь. Используй /reset чтобы начать разговор заново."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сбросить историю диалога."""
    user_id = update.effective_user.id
    user_sessions[user_id] = []
    await update.message.reply_text("История разговора сброшена. Начнем заново?")


def get_yandex_gpt_response(messages):
    """Получить ответ от Яндекс ГПТ с использованием SDK."""
    try:
        # Подготовка сообщений в формате для SDK
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "text": msg["text"]
            })

        # Создание запроса к модели
        request = llm.CompletionRequest(
            model_uri=f"gpt://{YANDEX_GPT_FOLDER_ID}/yandexgpt-lite",
            messages=formatted_messages,
            temperature=0.6,
            max_tokens=1500
        )

        # Выполнение запроса
        response = llm_client.completion(request)
        return response.result.alternatives[0].message.text
    except Exception as e:
        logger.error(f"Ошибка при обращении к Яндекс ГПТ: {e}")
        return "Извините, у меня возникли проблемы с получением ответа. Попробуйте еще раз позже."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка входящих сообщений."""
    user_id = update.effective_user.id
    user_message = update.message.text

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
    await update.message.chat.send_action(action="typing")

    # Получаем ответ от Яндекс ГПТ
    response = get_yandex_gpt_response(user_sessions[user_id])

    # Добавляем ответ ассистента в историю
    user_sessions[user_id].append({"role": "assistant", "text": response})

    # Отправляем ответ пользователю
    await update.message.reply_text(response)


def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))

    # Регистрация обработчика сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    main()