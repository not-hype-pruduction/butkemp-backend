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
        "Привет! Я твой бот-помощник по профориентации.\n"
        "Я помогу тебе разобраться в мире профессий и выбрать свой карьерный путь.",
        reply_markup=get_main_keyboard(False)
    )


# Функция для создания клавиатуры
def get_main_keyboard(is_career_assistant_active=False):
    builder = InlineKeyboardBuilder()

    if is_career_assistant_active:
        builder.add(types.InlineKeyboardButton(
            text="🛑 Отключить карьерного ассистента",
            callback_data="stop_psychologist"
        ))
    else:
        builder.add(types.InlineKeyboardButton(
            text="🧭 Карьерный ассистент",
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

    builder.add(types.InlineKeyboardButton(
        text="🧩 Профориентационный тест",
        callback_data="career_test"
    ))

    # Выравниваем кнопки по 1 в ряду
    builder.adjust(1)

    return builder.as_markup()

# Состояния пользователей в тесте
test_state = {}  # Словарь для хранения текущего вопроса
test_answers = {}  # Словарь для хранения ответов пользователя

# Вопросы теста
CAREER_TEST_QUESTIONS = [
    "Какие занятия вам больше всего нравятся в свободное время?",
    "Какие школьные предметы вам нравятся больше всего?",
    "Какими навыками вы гордитесь больше всего?",
    "Как вы предпочитаете работать: в команде или самостоятельно?",
    "Что для вас важнее в будущей профессии: высокий доход, стабильность, творческая реализация или помощь людям?"
]


# Обработчик для запуска профориентационного теста
@dp.callback_query(lambda c: c.data == "career_test")
async def start_career_test(callback: types.CallbackQuery):
    """Запуск профориентационного теста"""
    user_id = callback.from_user.id

    # Инициализируем состояние теста для пользователя
    test_state[user_id] = 0
    test_answers[user_id] = []

    await callback.message.answer(
        "🧩 *Профориентационный тест*\n\n"
        "Этот тест поможет вам определиться с выбором профессии. "
        "Я задам вам несколько вопросов о ваших интересах и предпочтениях, "
        "а затем дам рекомендации по подходящим профессиям.\n\n"
        "Готовы начать? Ответьте на первый вопрос:",
        parse_mode=ParseMode.MARKDOWN
    )

    # Отправляем первый вопрос
    await send_test_question(callback.message, user_id)
    await callback.answer("Тест запущен")


# Функция для отправки вопроса теста
async def send_test_question(message, user_id):
    if user_id in test_state and test_state[user_id] < len(CAREER_TEST_QUESTIONS):
        question_num = test_state[user_id] + 1
        question = CAREER_TEST_QUESTIONS[test_state[user_id]]

        # Создаем клавиатуру с кнопкой отмены
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="⬅️ Отменить тест",
            callback_data="back_to_main"
        ))

        await message.answer(
            f"*Вопрос {question_num}/{len(CAREER_TEST_QUESTIONS)}*\n\n{question}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup()
        )
    else:
        # Если вопросы закончились, генерируем результат
        await generate_test_result(message, user_id)


# Обработчик текстовых ответов на вопросы теста
@dp.message()
async def process_message(message: types.Message):
    """Обработка входящих сообщений."""
    user_id = message.from_user.id
    user_message = message.text

    # Если пользователь проходит тест и ответил на вопрос
    if user_id in test_state and 0 <= test_state[user_id] < len(CAREER_TEST_QUESTIONS):
        # Сохраняем ответ
        test_answers[user_id].append(user_message)

        # Переходим к следующему вопросу
        test_state[user_id] += 1

        # Отправляем следующий вопрос или результат
        await send_test_question(message, user_id)
        return

    # Если режим психолога не активен для пользователя, показываем клавиатуру
    if user_id not in psychologist_active or not psychologist_active[user_id]:
        await message.answer(
            "Для общения с психологом сначала активируйте этот режим",
            reply_markup=get_main_keyboard(False)
        )
        return

    # Обработка для режима психолога (существующий код)
    # Инициализируем сессию, если это первое сообщение
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # В функции process_message, где происходит обработка сообщений в режиме ассистента:
    if not user_sessions[user_id]:
        user_sessions[user_id].append({
            "role": "system",
            "text": "Ты карьерный консультант для школьников и студентов. Твоя задача - помогать с выбором профессии, образования и карьерного пути. Отвечай на вопросы о требованиях к разным профессиям, необходимых навыках, возможностях трудоустройства и перспективах в различных отраслях. Давай практичные советы по развитию карьеры и выбору образования. Будь информативным, объективным и мотивирующим."
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


# Функция для генерации результата теста
async def generate_test_result(message, user_id):
    # Отправляем "печатает..." статус
    await bot.send_chat_action(chat_id=user_id, action="typing")

    # Формируем вопросы и ответы для отправки в нейросеть
    qa_pairs = []
    for i, question in enumerate(CAREER_TEST_QUESTIONS):
        if i < len(test_answers[user_id]):
            qa_pairs.append(f"Вопрос: {question}")
            qa_pairs.append(f"Ответ: {test_answers[user_id][i]}")

    qa_text = "\n".join(qa_pairs)

    # Создаем запрос для получения результатов теста
    test_request = [
        {
            "role": "system",
            "text": "Ты профориентолог, эксперт по профессиональному ориентированию. Твоя задача - проанализировать ответы человека на вопросы и дать краткие, конкретные рекомендации по подходящим профессиям."
        },
        {
            "role": "user",
            "text": f"На основе ответов на вопросы профориентационного теста, определи подходящую профессиональную область и конкретные профессии для человека. Вот ответы:\n\n{qa_text}\n\nСформируй результат теста в краткой форме (не более 800 символов), включающий: 1) Основная профессиональная область (1-2 области максимум), 2) Топ-3 конкретные профессии, подходящие респонденту, 3) Ключевые навыки, которые стоит развивать. Используй маркированные списки и эмодзи для структурирования."
        }
    ]

    try:
        formatted_messages = []
        for msg in test_request:
            formatted_messages.append({
                'role': msg["role"],
                'text': msg["text"]
            })

        operation = model.run_deferred(formatted_messages)
        result = operation.wait().text

        # Создаем клавиатуру для действий после теста
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="🔄 Пройти тест заново",
            callback_data="career_test"
        ))
        builder.add(types.InlineKeyboardButton(
            text="🎓 Изучить профессии",
            callback_data="career_guidance"
        ))
        builder.add(types.InlineKeyboardButton(
            text="⬅️ В главное меню",
            callback_data="back_to_main"
        ))
        builder.adjust(1)

        # Отправляем результат
        await message.answer(
            "✨ *Результаты профориентационного теста* ✨\n\n" + result,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup()
        )

    except Exception as e:
        logger.error(f"Ошибка при генерации результатов теста: {e}")
        await message.answer(
            "К сожалению, произошла ошибка при анализе результатов теста. Попробуйте пройти тест еще раз.",
            reply_markup=get_main_keyboard(False)
        )

    # Очищаем данные теста
    if user_id in test_state:
        del test_state[user_id]
    if user_id in test_answers:
        del test_answers[user_id]

# Словари для хранения состояний пользователей в режиме профориентации
professions = {}  # Выбранная профессия
lectures = {}     # Выбранная лекция
current_lecture = {}  # Текущая лекция
course_progress = {}  # хранит данные о текущей секции курса, ожидании ответа и т.д.
user_answers = {}
PROFESSIONS_LECTURES = {
    "doctor": {
        "name": "Врач",
        "lectures": {
            "vision": {
                "title": "Дальтонизм",
                "sections": [
                    {
                        "type": "theory",
                        "content": """**Курс «Профориентация в медицине: знакомство с дальтонизмом»**

Этот курс поможет тебе, старшекласснику, почувствовать себя начинающим врачом-офтальмологом и разобраться в том, что такое дальтонизм. Всё просто, весело и интерактивно, как в Duolingo: коротко теория — сразу практика — подсказка с ответом.

## 1. Введение: Ты — врач-стажёр 🩺

Представь, что ты впервые приходишь в приёмную офтальмолога. У тебя белый халат, фонарик и планшет. Твоя задача — помочь людям правильно определять цвета и цифры на тестах, чтобы выявить дальтонизм. Готов? Поехали!"""
                    },
                    {
                        "type": "theory",
                        "content": """## 2. Немного истории 📜

- **1794**: английский астроном Джон Дальтон первым описал свою неспособность видеть красный и зелёный цвета.
- Он назвал это «цветовой слепотой», но вскоре термин сменился на «дальтонизм».
- Сейчас мы знаем, что дальтонизм встречается у ~8% мужчин и ~0.5% женщин."""
                    },
                    {
                        "type": "quiz",
                        "question": "Как ты думаешь, почему мужчинам дальтонизм встречается чаще?",
                        "options": [
                            "A) Потому что они больше смотрят на компьютеры",
                            "B) Из-за особенностей генов на X-хромосоме",
                            "C) Потому что хуже питаются"
                        ],
                        "correct_answer": "B",
                        "explanation": "Правильный ответ: B — Из-за особенностей генов на X-хромосоме. Мужчины имеют только одну X-хромосому, поэтому при наличии на ней дефектного гена дальтонизма это состояние проявится. У женщин две X-хромосомы, и для проявления дальтонизма дефект должен быть на обеих."
                    },
                    {
                        "type": "theory",
                        "content": """## 3. Теория: что такое дальтонизм? 🧠

1. **Фоторецепторы в глазах**: колбочки отвечают за восприятие красного, зелёного и синего цвета.
2. **При дальтонизме** одна из групп колбочек работает иначе или не работает совсем.
3. **Типы дальтонизма**:
   - Протанопия (¬ красный)
   - Дейтеранопия (¬ зелёный)
   - Тританопия (¬ синий)"""
                    },
                    {
                        "type": "quiz",
                        "question": "Ты врач, пациент не видит зелёных яблок на картинке. Какой тип дальтонизма можно предположить?",
                        "options": [
                            "A) Протанопия",
                            "B) Дейтеранопия",
                            "C) Тританопия"
                        ],
                        "correct_answer": "B",
                        "explanation": "Правильный ответ: B — дейтеранопия. При дейтеранопии нарушено восприятие зеленого цвета из-за дисфункции колбочек, отвечающих за восприятие зеленого спектра."
                    },
                    {
                        "type": "open_question",
                        "question": "Почему важно выявлять дальтонизм у детей школьного возраста?",
                        "keywords": ["учеба", "обучение", "профессия", "безопасность", "адаптация", "помощь"],
                        "explanation": "Раннее выявление дальтонизма важно для адаптации учебного процесса, профориентации (некоторые профессии недоступны при дальтонизме), а также для обеспечения безопасности ребенка (например, распознавание сигналов светофора)."
                    }
                ]
            },
            "anatomy": {
                "title": "Анатомия и физиология",
                "content": "Содержание лекции по анатомии и физиологии..."
            },
            "diagnosis": {
                "title": "Диагностика заболеваний",
                "content": "Содержание лекции по диагностике заболеваний..."
            },
            "emergency": {
                "title": "Неотложная помощь",
                "content": "Содержание лекции по неотложной помощи..."
            }
        }
    },
    "programmer": {
        "name": "Программист",
        "lectures": {
            "basics": {
                "title": "Основы программирования",
                "content": "Содержание лекции по основам программирования..."
            },
            "web": {
                "title": "Веб-разработка",
                "content": "Содержание лекции по веб-разработке..."
            },
            "mobile": {
                "title": "Разработка мобильных приложений",
                "content": "Содержание лекции по разработке мобильных приложений..."
            },
            "ai": {
                "title": "Искусственный интеллект",
                "content": "Содержание лекции по искусственному интеллекту..."
            }
        }
    }
    # Аналогично для других профессий
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

    # Запускаем первую секцию курса
    await show_course_section(callback.message, user_id, profession_key, lecture_key, 0)
    await callback.answer(f"Начинаем курс: {PROFESSIONS_LECTURES[profession_key]['lectures'][lecture_key]['title']}")


@dp.callback_query(lambda c: c.data and c.data.startswith("profession_"))
async def select_profession(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    profession_key = callback.data.split("_")[1]

    # Сохраняем выбор профессии
    professions[user_id] = profession_key

    await callback.message.answer(
        f"Вы выбрали профессию: *{PROFESSIONS_LECTURES[profession_key]['name']}*\n\n"
        f"Выберите лекцию для изучения:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_lectures_keyboard(profession_key)
    )
    await callback.answer(f"Выбрана профессия: {PROFESSIONS_LECTURES[profession_key]['name']}")

@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_active = psychologist_active.get(user_id, False)

    # При возврате в главное меню сбрасываем прогресс текущего курса
    if user_id in course_progress:
        course_progress[user_id]["waiting_for_answer"] = False

    await callback.message.answer(
        "Вы вернулись в главное меню. Выберите действие:",
        reply_markup=get_main_keyboard(is_active)
    )
    await callback.answer("Главное меню")


async def show_course_section(message, user_id, profession_key, lecture_key, section_index=0):
    # Проверка наличия профессии и лекции в словаре
    if profession_key not in PROFESSIONS_LECTURES:
        await message.answer("Ошибка: профессия не найдена.")
        return

    if lecture_key not in PROFESSIONS_LECTURES[profession_key]["lectures"]:
        await message.answer("Ошибка: лекция не найдена.")
        return

    # Получаем информацию о курсе
    lecture = PROFESSIONS_LECTURES[profession_key]["lectures"][lecture_key]

    # Проверка формата лекции (новый со sections или старый с content)
    if "sections" in lecture:
        sections = lecture["sections"]

        # Проверяем, находится ли индекс в диапазоне
        if not sections or section_index < 0 or section_index >= len(sections):
            await message.answer("Ошибка: секция не найдена.")
            return

        # Получаем текущую секцию
        section = sections[section_index]
        section_type = section.get("type", "theory")

        # Сохраняем текущую позицию пользователя
        course_progress[user_id] = {
            "profession": profession_key,
            "lecture": lecture_key,
            "section": section_index,
            "waiting_for_answer": False
        }

        # Создаем клавиатуру навигации
        builder = InlineKeyboardBuilder()

        # Если это не первая секция, добавляем кнопку "Назад"
        if section_index > 0:
            builder.add(types.InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"course_{profession_key}_{lecture_key}_{section_index - 1}"
            ))

        # Если это теория и не последняя секция, добавляем кнопку "Дальше"
        if section_type == "theory" and section_index < len(sections) - 1:
            builder.add(types.InlineKeyboardButton(
                text="Дальше ➡️",
                callback_data=f"course_{profession_key}_{lecture_key}_{section_index + 1}"
            ))

        # Добавляем кнопку к списку лекций
        builder.add(types.InlineKeyboardButton(
            text="🔙 К списку лекций",
            callback_data=f"profession_{profession_key}"
        ))

        # Добавляем кнопку выхода в главное меню
        builder.add(types.InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data="back_to_main"
        ))

        # Выравниваем кнопки по одной в строке
        builder.adjust(1)

        # Обработка в зависимости от типа секции
        if section_type == "theory":
            # Отправляем теоретический материал
            await message.answer(
                section["content"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=builder.as_markup()
            )

        elif section_type == "quiz":
            # Создаем клавиатуру с вариантами ответов
            options_builder = InlineKeyboardBuilder()

            # Добавляем кнопки с вариантами ответов
            for i, option in enumerate(section["options"]):
                option_letter = chr(65 + i)  # A, B, C, D...
                options_builder.add(types.InlineKeyboardButton(
                    text=f"{option_letter}. {option}",
                    callback_data=f"answer_{profession_key}_{lecture_key}_{section_index}_{option_letter}"
                ))

            # Добавляем кнопки навигации
            options_builder.add(types.InlineKeyboardButton(
                text="🔙 К списку лекций",
                callback_data=f"profession_{profession_key}"
            ))
            options_builder.add(types.InlineKeyboardButton(
                text="🏠 В главное меню",
                callback_data="back_to_main"
            ))

            options_builder.adjust(1)  # По одной кнопке в ряду

            await message.answer(
                f"**Вопрос:**\n\n{section['question']}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=options_builder.as_markup()
            )

        elif section_type == "open_question":
            # Отмечаем, что ждем ответ на открытый вопрос
            course_progress[user_id]["waiting_for_answer"] = True

            # Отправляем открытый вопрос
            await message.answer(
                f"**Практика:**\n\n{section['question']}\n\nВведите ваш ответ в чат.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=builder.as_markup()
            )
    else:
        # Старый формат с единым контентом
        await message.answer(
            lecture["content"],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_lectures_keyboard(profession_key)
        )


def get_back_to_lectures_keyboard(profession_key):
    """Создает клавиатуру с кнопкой возврата к списку лекций."""
    builder = InlineKeyboardBuilder()

    builder.add(types.InlineKeyboardButton(
        text="🔙 К списку лекций",
        callback_data=f"profession_{profession_key}"
    ))

    builder.add(types.InlineKeyboardButton(
        text="🏠 В главное меню",
        callback_data="back_to_main"
    ))

    builder.adjust(1)
    return builder.as_markup()


# Обработчик для навигации по секциям курса
@dp.callback_query(lambda c: c.data and c.data.startswith("course_"))
async def course_navigation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, profession_key, lecture_key, section_index = callback.data.split("_")
    section_index = int(section_index)

    await show_course_section(callback.message, user_id, profession_key, lecture_key, section_index)
    await callback.answer()


# Обработчик для проверки ответов на вопросы с вариантами
@dp.callback_query(lambda c: c.data and c.data.startswith("answer_"))
async def check_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, profession_key, lecture_key, section_index, user_answer = callback.data.split("_")
    section_index = int(section_index)

    # Получаем информацию о секции
    section = PROFESSIONS_LECTURES[profession_key]["lectures"][lecture_key]["sections"][section_index]
    correct_answer = section["correct_answer"]
    explanation = section["explanation"]

    # Проверяем ответ
    if user_answer == correct_answer:
        result_message = "✅ Правильно! " + explanation
    else:
        result_message = f"❌ Неверно. {explanation}"

    # Создаем клавиатуру для перехода к следующей секции
    builder = InlineKeyboardBuilder()

    # Если есть следующая секция, добавляем кнопку перехода
    if section_index < len(PROFESSIONS_LECTURES[profession_key]["lectures"][lecture_key]["sections"]) - 1:
        builder.add(types.InlineKeyboardButton(
            text="Следующий шаг ➡️",
            callback_data=f"course_{profession_key}_{lecture_key}_{section_index + 1}"
        ))

    # Добавляем кнопки навигации
    builder.add(types.InlineKeyboardButton(
        text="🔄 К списку лекций",
        callback_data=f"profession_{profession_key}"
    ))
    builder.add(types.InlineKeyboardButton(
        text="⬅️ В главное меню",
        callback_data="back_to_main"
    ))
    builder.adjust(1)

    await callback.message.answer(
        result_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# Клавиатура для выбора лекции
def get_lectures_keyboard(profession_key):
    builder = InlineKeyboardBuilder()

    for lecture_key, lecture_data in PROFESSIONS_LECTURES[profession_key]["lectures"].items():
        builder.add(types.InlineKeyboardButton(
            text=lecture_data["title"],
            callback_data=f"lecture_{lecture_key}"
        ))

    # Кнопка возврата к выбору профессии
    builder.add(types.InlineKeyboardButton(
        text="⬅️ Назад к списку профессий",
        callback_data="career_guidance"
    ))

    builder.adjust(1)
    return builder.as_markup()


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
async def start_career_assistant(callback: types.CallbackQuery):
    """Активирует режим карьерного ассистента."""
    user_id = callback.from_user.id
    psychologist_active[user_id] = True  # Оставляем имя переменной для совместимости

    await callback.message.answer(
        "🧭 *Карьерный ассистент активирован*\n\n"
        "Теперь вы можете задавать мне вопросы о выборе профессии, карьерном пути, "
        "необходимом образовании или навыках для работы в различных сферах.\n\n"
        "Я помогу вам разобраться в особенностях разных профессий и направлений.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(True)
    )
    await callback.answer("Карьерный ассистент активирован")


@dp.callback_query(lambda c: c.data == "stop_psychologist")
async def stop_career_assistant(callback: types.CallbackQuery):
    """Деактивирует режим карьерного ассистента."""
    user_id = callback.from_user.id
    psychologist_active[user_id] = False

    await callback.message.answer(
        "Режим карьерного ассистента отключен. Выберите нужную функцию:",
        reply_markup=get_main_keyboard(False)
    )
    await callback.answer("Карьерный ассистент отключен")



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

    # Проверяем, ожидаем ли мы ответ на открытый вопрос
    if user_id in course_progress and course_progress[user_id].get("waiting_for_answer", False):
        # Получаем информацию о текущем вопросе
        prof_key = course_progress[user_id]["profession"]
        lect_key = course_progress[user_id]["lecture"]
        section_idx = course_progress[user_id]["section"]

        # Получаем секцию с вопросом
        section = PROFESSIONS_LECTURES[prof_key]["lectures"][lect_key]["sections"][section_idx]

        # Проверяем наличие ключевых слов в ответе
        keywords = section["keywords"]
        found_keywords = [word for word in keywords if word.lower() in user_message.lower()]

        # Определяем качество ответа
        if found_keywords:
            feedback = f"✅ Хороший ответ! Вы упомянули важные аспекты: {', '.join(found_keywords)}.\n\n"
        else:
            feedback = "🤔 Интересный ответ, но вот важные моменты, которые стоило бы учесть:\n\n"

        # Добавляем объяснение
        feedback += section["explanation"]

        # Обновляем состояние пользователя
        course_progress[user_id]["waiting_for_answer"] = False

        # Создаем клавиатуру для перехода к следующей секции
        builder = InlineKeyboardBuilder()

        # Если есть следующая секция, добавляем кнопку перехода
        if section_idx < len(PROFESSIONS_LECTURES[prof_key]["lectures"][lect_key]["sections"]) - 1:
            builder.add(types.InlineKeyboardButton(
                text="Следующий шаг ➡️",
                callback_data=f"course_{prof_key}_{lect_key}_{section_idx + 1}"
            ))

        # Добавляем кнопки навигации
        builder.add(types.InlineKeyboardButton(
            text="🔄 К списку лекций",
            callback_data=f"profession_{prof_key}"
        ))
        builder.add(types.InlineKeyboardButton(
            text="⬅️ В главное меню",
            callback_data="back_to_main"
        ))
        builder.adjust(1)

        await message.answer(
            feedback,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup()
        )
        return

    # Если пользователь проходит тест и ответил на вопрос
    if user_id in test_state and 0 <= test_state[user_id] < len(CAREER_TEST_QUESTIONS):
        # Сохраняем ответ
        test_answers[user_id].append(user_message)

        # Переходим к следующему вопросу
        test_state[user_id] += 1

        # Отправляем следующий вопрос или результат
        await send_test_question(message, user_id)
        return

    # Если режим психолога не активен для пользователя, показываем клавиатуру
    if user_id not in psychologist_active or not psychologist_active[user_id]:
        await message.answer(
            "Для общения с карьерным ассистентом сначала активируйте этот режим",
            reply_markup=get_main_keyboard(False)
        )
        return

    # Обработка для режима психолога/карьерного ассистента
    # Инициализируем сессию, если это первое сообщение
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Добавляем системное сообщение, если история пуста
    if not user_sessions[user_id]:
        user_sessions[user_id].append({
            "role": "system",
            "text": "Ты карьерный консультант для школьников и студентов. Твоя задача - помогать с выбором профессии, образования и карьерного пути. Отвечай на вопросы о требованиях к разным профессиям, необходимых навыках, возможностях трудоустройства и перспективах в различных отраслях. Давай практичные советы по развитию карьеры и выбору образования. Будь информативным, объективным и мотивирующим."
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