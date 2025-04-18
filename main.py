import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.enums.parse_mode import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
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

# История сообщений и статус бота-ассистента для каждого пользователя
user_sessions = {}
assistant_active = {}  # Словарь для отслеживания активности режима ассистента

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

# Функция для создания клавиатуры
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="📚 Запустить учебного ассистента",
        callback_data="start_assistant"
    ))
    builder.add(types.InlineKeyboardButton(
        text="🛑 Остановить учебного ассистента",
        callback_data="stop_assistant"
    ))
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start."""
    user_id = message.from_user.id
    user_sessions[user_id] = []
    assistant_active[user_id] = False

    await message.answer(
        "Привет! Я твой учебный ассистент.\n"
        "Нажми на кнопку, чтобы активировать режим помощи с учёбой.",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "start_assistant")
async def start_assistant(callback: types.CallbackQuery):
    """Активация режима учебного ассистента"""
    user_id = callback.from_user.id
    assistant_active[user_id] = True

    if user_id not in user_sessions:
        user_sessions[user_id] = []

    await callback.message.answer(
        "Режим учебного ассистента активирован! 📚\n"
        "Я готов помочь тебе с учебой, экзаменами, поступлением в вуз и другими школьными вопросами.\n"
        "Напиши, что тебя интересует?"
    )
    await callback.answer("Учебный ассистент готов помогать!")

@dp.callback_query(lambda c: c.data == "stop_assistant")
async def stop_assistant(callback: types.CallbackQuery):
    """Деактивация режима ассистента"""
    user_id = callback.from_user.id
    assistant_active[user_id] = False

    await callback.message.answer(
        "Режим учебного ассистента отключен. Вернулись в основное меню.",
        reply_markup=get_main_keyboard()
    )
    await callback.answer("Учебный ассистент отключен")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработка команды /help."""
    await message.answer(
        "Я твой учебный ассистент! 📚\n"
        "Для активации режима помощи нажми на соответствующую кнопку.\n"
        "Я могу помочь тебе:\n"
        "• С домашними заданиями и сложными темами\n"
        "• С подготовкой к ОГЭ/ЕГЭ/экзаменам\n"
        "• С выбором вуза и специальности\n"
        "• С организацией учебного процесса\n\n"
        "Используй /reset чтобы сбросить историю разговора.",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    """Сбросить историю диалога."""
    user_id = message.from_user.id
    user_sessions[user_id] = []
    await message.answer("История разговора сброшена.", reply_markup=get_main_keyboard())

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

    # Если режим ассистента не активен для пользователя, показываем клавиатуру
    if user_id not in assistant_active or not assistant_active[user_id]:
        await message.answer(
            "Для получения помощи с учёбой сначала активируй режим учебного ассистента",
            reply_markup=get_main_keyboard()
        )
        return

    # Инициализируем сессию, если это первое сообщение
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Добавляем системное сообщение, если это первое сообщение
    if not user_sessions[user_id]:
        user_sessions[user_id].append({
            "role": "system",
            "text": "Ты учебный ассистент для школьников. Твоя задача - помогать с учебой, объяснять сложные темы, давать советы по подготовке к экзаменам (ОГЭ, ЕГЭ), помогать с выбором вуза и специальности, давать рекомендации по организации учебного процесса. Объясняй материал понятно, с примерами. Если нужно, предлагай способы запоминания. Будь дружелюбным и мотивирующим. Не рекомендуй готовые решения для списывания."
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