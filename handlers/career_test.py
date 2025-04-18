from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import get_main_keyboard
from utils.storage import test_state, test_answers
from data.test_questions import CAREER_TEST_QUESTIONS, TEST_INTERPRETATIONS

router = Router()


@router.callback_query(F.data == "career_test")
async def start_career_test(callback: CallbackQuery):
    """Начало профориентационного теста"""
    user_id = callback.from_user.id

    # Инициализируем состояние теста
    test_state[user_id] = 0
    test_answers[user_id] = []

    await callback.message.answer(
        "🧩 <b>Профориентационный тест</b>\n\n"
        "Я задам вам несколько вопросов, чтобы лучше понять ваши интересы и склонности.\n"
        "Отвечайте подробно, это поможет точнее определить подходящие профессии.\n\n"
        f"<b>Вопрос 1 из {len(CAREER_TEST_QUESTIONS)}:</b>\n{CAREER_TEST_QUESTIONS[0]}"
    )
    await callback.answer()


@router.message(lambda message: message.from_user.id in test_state and test_state[message.from_user.id] < len(
    CAREER_TEST_QUESTIONS))
async def process_test_answer(message: Message):
    """Обработка ответов на вопросы теста"""
    user_id = message.from_user.id

    # Сохраняем ответ
    test_answers[user_id].append(message.text)
    test_state[user_id] += 1

    if test_state[user_id] < len(CAREER_TEST_QUESTIONS):
        # Задаем следующий вопрос
        current_question = test_state[user_id]
        await message.answer(
            f"<b>Вопрос {current_question + 1} из {len(CAREER_TEST_QUESTIONS)}:</b>\n"
            f"{CAREER_TEST_QUESTIONS[current_question]}"
        )
    else:
        # Тест завершен, анализируем ответы
        await analyze_test_results(message, user_id)


async def analyze_test_results(message: Message, user_id: int):
    """Анализ результатов теста и вывод рекомендаций"""
    # В реальном приложении здесь будет более сложная логика анализа
    # Для примера просто объединяем все ответы и ищем ключевые слова

    all_answers = " ".join(test_answers[user_id]).lower()

    # Определяем направленность по ключевым словам (примитивный алгоритм для примера)
    result_types = []

    if any(word in all_answers for word in ["компьютер", "программирование", "техника", "технологии"]):
        result_types.append("технический")

    if any(word in all_answers for word in ["творчество", "искусство", "рисовать", "музыка"]):
        result_types.append("творческий")

    if any(word in all_answers for word in ["люди", "общение", "помощь", "психология"]):
        result_types.append("социальный")

    if any(word in all_answers for word in ["исследования", "анализ", "наука", "изучение"]):
        result_types.append("исследовательский")

    if any(word in all_answers for word in ["бизнес", "деньги", "руководство", "лидерство"]):
        result_types.append("предприимчивый")

    # Если ничего не определено, даем общую рекомендацию
    if not result_types:
        result_types.append("технический")

    # Формируем результат
    result_text = "🎯 <b>Результаты профориентационного теста:</b>\n\n"

    for result_type in result_types:
        result_text += f"• {TEST_INTERPRETATIONS[result_type]}\n\n"

    result_text += "Для более детального анализа рекомендуем обратиться к профессиональному карьерному консультанту."

    # Создаем кнопку для возврата в меню
    builder = InlineKeyboardBuilder()
    builder.add(F.text("⬅️ Вернуться в главное меню", callback_data="back_to_menu"))

    await message.answer(result_text, reply_markup=builder.as_markup())

    # Очищаем состояние теста
    del test_state[user_id]
    del test_answers[user_id]


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.answer(
        "Вы вернулись в главное меню:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)