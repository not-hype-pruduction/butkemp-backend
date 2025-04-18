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

# История сообщений и статус режима психолога для каждого пользователя
user_sessions = {}
psychologist_active = {}  # Словарь для отслеживания активности режима психолога

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
def get_main_keyboard(is_psychologist_active=False):
    builder = InlineKeyboardBuilder()

    if is_psychologist_active:
        builder.add(types.InlineKeyboardButton(
            text="🛑 Выключить психолога",
            callback_data="stop_psychologist"
        ))
    else:
        builder.add(types.InlineKeyboardButton(
            text="🧠 Режим психолога",
            callback_data="start_psychologist"
        ))

    return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start."""
    user_id = message.from_user.id
    user_sessions[user_id] = []
    psychologist_active[user_id] = False

    await message.answer(
        "Привет! Я твой ассистент.\n"
        "Одна из моих функций - режим психолога. Нажми на кнопку, чтобы активировать его.",
        reply_markup=get_main_keyboard(False)
    )


# Функция для создания клавиатуры
def get_main_keyboard(is_psychologist_active=False):
    builder = InlineKeyboardBuilder()

    if is_psychologist_active:
        builder.add(types.InlineKeyboardButton(
            text="🛑 Выключить психолога",
            callback_data="stop_psychologist"
        ))
    else:
        builder.add(types.InlineKeyboardButton(
            text="🧠 Режим психолога",
            callback_data="start_psychologist"
        ))

    # Добавляем кнопку для получения рецепта блинов
    builder.add(types.InlineKeyboardButton(
        text="🥞 Получить рецепт блинов",
        callback_data="pancake_recipe"
    ))

    # Добавляем кнопку режима профориентации
    builder.add(types.InlineKeyboardButton(
        text="🎓 Профориентация",
        callback_data="career_guidance"
    ))

    # Выравниваем кнопки по 1 в ряду
    builder.adjust(1)

    return builder.as_markup()


# Словари для хранения состояний пользователей в режиме профориентации
professions = {}  # Выбранная профессия
lectures = {}     # Выбранная лекция
current_lecture = {}  # Текущая лекция

# Профессии и лекции
PROFESSIONS_LECTURES = {
    "programmer": {
        "name": "Программист",
        "lectures": {
            "basics": "Основы программирования",
            "web": "Веб-разработка",
            "mobile": "Разработка мобильных приложений",
            "ai": "Искусственный интеллект"
        }
    },
    "doctor": {
        "name": "Врач",
        "lectures": {
            "anatomy": "Анатомия и физиология",
            "diagnosis": "Диагностика заболеваний",
            "treatment": "Методы лечения",
            "emergency": "Неотложная помощь"
        }
    },
    "designer": {
        "name": "Дизайнер",
        "lectures": {
            "graphics": "Графический дизайн",
            "ui": "UI/UX дизайн",
            "3d": "3D моделирование",
            "animation": "Анимация"
        }
    }
}


# Обработчик для режима профориентации
@dp.callback_query(lambda c: c.data == "career_guidance")
async def career_guidance_mode(callback: types.CallbackQuery):
    """Запуск режима профориентации"""
    user_id = callback.from_user.id

    await callback.message.answer(
        "🎓 *Режим профориентации*\n\n"
        "Выберите профессию, о которой хотите узнать больше:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_professions_keyboard()
    )
    await callback.answer("Выберите профессию")


# Клавиатура для выбора профессии
def get_professions_keyboard():
    builder = InlineKeyboardBuilder()

    for prof_key, prof_data in PROFESSIONS_LECTURES.items():
        builder.add(types.InlineKeyboardButton(
            text=prof_data["name"],
            callback_data=f"profession_{prof_key}"
        ))

    # Кнопка возврата в главное меню
    builder.add(types.InlineKeyboardButton(
        text="⬅️ Вернуться в меню",
        callback_data="back_to_main"
    ))

    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()


# Обработчик выбора профессии
@dp.callback_query(lambda c: c.data and c.data.startswith("profession_"))
async def select_profession(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    profession_key = callback.data.split("_")[1]

    # Сохраняем выбор пользователя
    professions[user_id] = profession_key

    await callback.message.answer(
        f"Вы выбрали профессию: *{PROFESSIONS_LECTURES[profession_key]['name']}*\n\n"
        "Выберите интересующую вас лекцию:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_lectures_keyboard(profession_key)
    )
    await callback.answer(f"Выбрана профессия: {PROFESSIONS_LECTURES[profession_key]['name']}")


# Клавиатура для выбора лекции
def get_lectures_keyboard(profession_key):
    builder = InlineKeyboardBuilder()

    for lecture_key, lecture_name in PROFESSIONS_LECTURES[profession_key]["lectures"].items():
        builder.add(types.InlineKeyboardButton(
            text=lecture_name,
            callback_data=f"lecture_{lecture_key}"
        ))

    # Кнопка возврата к выбору профессии
    builder.add(types.InlineKeyboardButton(
        text="⬅️ Назад к списку профессий",
        callback_data="career_guidance"
    ))

    builder.adjust(1)
    return builder.as_markup()


# Обработчик выбора лекции
@dp.callback_query(lambda c: c.data and c.data.startswith("lecture_"))
async def select_lecture(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lecture_key = callback.data.split("_")[1]

    if user_id not in professions:
        await callback.message.answer(
            "Пожалуйста, сначала выберите профессию.",
            reply_markup=get_professions_keyboard()
        )
        await callback.answer("Нужно выбрать профессию")
        return

    # Сохраняем выбор лекции
    lectures[user_id] = lecture_key
    profession_key = professions[user_id]

    # Отправляем статус "печатает..."
    await bot.send_chat_action(chat_id=user_id, action="typing")

    # Генерируем лекцию с помощью ИИ
    prompt = [
        {
            "role": "system",
            "text": "Ты эксперт по профориентации. Создавай информативные и вдохновляющие лекции о разных аспектах профессий для школьников и студентов."
        },
        {
            "role": "user",
            "text": f"Создай познавательную лекцию о профессии '{PROFESSIONS_LECTURES[profession_key]['name']}', направление '{PROFESSIONS_LECTURES[profession_key]['lectures'][lecture_key]}'. Лекция должна включать: основные понятия, необходимые навыки, возможности трудоустройства, примеры задач из реальной практики и советы начинающим. Используй эмодзи и форматирование для лучшего восприятия."
        }
    ]

    try:
        formatted_messages = []
        for msg in prompt:
            formatted_messages.append({
                'role': msg["role"],
                'text': msg["text"]
            })

        operation = model.run_deferred(formatted_messages)
        lecture_text = operation.wait().text

        # Сохраняем лекцию для пользователя
        current_lecture[user_id] = lecture_text

        # Создаем клавиатуру для действий с лекцией
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="🔄 Другая лекция",
            callback_data=f"profession_{profession_key}"
        ))
        builder.add(types.InlineKeyboardButton(
            text="🎓 Другая профессия",
            callback_data="career_guidance"
        ))
        builder.add(types.InlineKeyboardButton(
            text="⬅️ В главное меню",
            callback_data="back_to_main"
        ))
        builder.adjust(1)

        # Отправляем лекцию
        await callback.message.answer(
            lecture_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup()
        )

    except Exception as e:
        logger.error(f"Ошибка при генерации лекции: {e}")
        await callback.message.answer(
            "Извините, не удалось сгенерировать лекцию. Пожалуйста, попробуйте позже.",
            reply_markup=get_lectures_keyboard(profession_key)
        )

    await callback.answer("Лекция подготовлена")



# Добавляем обработчик для кнопки с рецептом блинов
@dp.callback_query(lambda c: c.data == "pancake_recipe")
async def get_pancake_recipe(callback: types.CallbackQuery):
    """Отправляет рецепт блинов, сгенерированный нейросетью"""
    user_id = callback.from_user.id
    is_active = psychologist_active.get(user_id, False)

    # Отправляем "печатает..." статус
    await bot.send_chat_action(chat_id=user_id, action="typing")

    # Создаем запрос для получения рецепта блинов
    recipe_request = [
        {
            "role": "system",
            "text": "Ты кулинарный эксперт. Создавай оригинальные рецепты блинов с подробными пошаговыми инструкциями."
        },
        {
            "role": "user",
            "text": "Сгенерируй интересный рецепт блинов. Включи ингредиенты, пошаговую инструкцию и советы. Формат ответа должен быть красивым и структурированным с эмодзи."
        }
    ]

    try:
        # Выполнение запроса к модели
        formatted_messages = []
        for msg in recipe_request:
            formatted_messages.append({
                'role': msg["role"],
                'text': msg["text"]
            })

        operation = model.run_deferred(formatted_messages)
        recipe = operation.wait().text

        await callback.message.answer(
            recipe,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(is_active)
        )
    except Exception as e:
        logger.error(f"Ошибка при генерации рецепта: {e}")
        await callback.message.answer(
            "Извините, не удалось сгенерировать рецепт блинов. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard(is_active)
        )

    await callback.answer("Рецепт блинов сгенерирован!")

@dp.callback_query(lambda c: c.data == "start_psychologist")
async def start_psychologist(callback: types.CallbackQuery):
    """Активация режима психолога"""
    user_id = callback.from_user.id
    psychologist_active[user_id] = True

    if user_id not in user_sessions:
        user_sessions[user_id] = []

    await callback.message.answer(
        "Режим психолога активирован! 🧠\n"
        "Я готов помочь тебе с проблемами в учебе, подготовкой к экзаменам, выбором вуза и другими школьными вопросами.\n"
        "Расскажи, что тебя беспокоит?",
        reply_markup=get_main_keyboard(True)
    )
    await callback.answer("Режим психолога активирован!")


@dp.callback_query(lambda c: c.data == "stop_psychologist")
async def stop_psychologist(callback: types.CallbackQuery):
    """Деактивация режима психолога"""
    user_id = callback.from_user.id
    psychologist_active[user_id] = False

    await callback.message.answer(
        "Режим психолога отключен. Вернулись в основное меню.",
        reply_markup=get_main_keyboard(False)
    )
    await callback.answer("Режим психолога отключен")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    is_active = psychologist_active.get(user_id, False)

    await message.answer(
        "Я твой ассистент!\n"
        "Одна из моих функций - режим психолога.\n"
        "В этом режиме я могу помочь тебе:\n"
        "• Справиться со стрессом от учебы\n"
        "• Подготовиться к экзаменам (ОГЭ/ЕГЭ)\n"
        "• С выбором вуза и специальности\n"
        "• С проблемами в школе\n\n"
        "Используй /reset чтобы сбросить историю разговора.",
        reply_markup=get_main_keyboard(is_active)
    )


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    """Сбросить историю диалога."""
    user_id = message.from_user.id
    user_sessions[user_id] = []
    is_active = psychologist_active.get(user_id, False)

    await message.answer(
        "История разговора сброшена.",
        reply_markup=get_main_keyboard(is_active)
    )


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

    # Если режим психолога не активен для пользователя, показываем клавиатуру
    if user_id not in psychologist_active or not psychologist_active[user_id]:
        await message.answer(
            "Для общения с психологом сначала активируйте этот режим",
            reply_markup=get_main_keyboard(False)
        )
        return

    # Инициализируем сессию, если это первое сообщение
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Добавляем системное сообщение, если это первое сообщение
    if not user_sessions[user_id]:
        user_sessions[user_id].append({
            "role": "system",
            "text": "Ты психолог для школьников и студентов. Твоя задача - поддерживать диалог, проявлять эмпатию и помогать с проблемами, связанными с учебой: стрессом от экзаменов, выбором университета, сложностями в учебе, проблемами с концентрацией, тревогой перед ОГЭ/ЕГЭ. Объясняй свои рекомендации понятно, давай практичные советы. Будь дружелюбным и мотивирующим."
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