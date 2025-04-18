from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards import get_main_keyboard
from utils.storage import psychologist_active, user_sessions
from models.yandex_gpt import get_yandex_gpt_response

router = Router()

SYSTEM_PROMPT = """Ты - карьерный консультант. 
Помогай пользователям с вопросами о карьере, образовании и профессиональном развитии.
Давай краткие, но информативные советы. Будь вежливым и поддерживающим."""


@router.callback_query(F.data == "start_psychologist")
async def start_career_assistant(callback: CallbackQuery):
    """Активация режима карьерного ассистента"""
    user_id = callback.from_user.id
    psychologist_active[user_id] = True

    # Инициализируем историю диалога с системным промптом
    user_sessions[user_id] = [
        {"role": "system", "text": SYSTEM_PROMPT}
    ]

    await callback.message.answer(
        "🧭 Карьерный ассистент активирован. Задайте любой вопрос о карьере, образовании или профессиональном развитии.",
        reply_markup=get_main_keyboard(is_career_assistant_active=True)
    )
    await callback.answer()


@router.callback_query(F.data == "stop_psychologist")
async def stop_career_assistant(callback: CallbackQuery):
    """Деактивация режима карьерного ассистента"""
    user_id = callback.from_user.id
    psychologist_active[user_id] = False

    await callback.message.answer(
        "🧭 Карьерный ассистент отключен. Вы вернулись в главное меню.",
        reply_markup=get_main_keyboard(is_career_assistant_active=False)
    )
    await callback.answer()


@router.message(lambda message: psychologist_active.get(message.from_user.id, False))
async def handle_assistant_message(message: Message):
    """Обработка сообщений в режиме карьерного ассистента"""
    user_id = message.from_user.id

    # Добавляем сообщение пользователя в историю
    user_sessions[user_id].append(
        {"role": "user", "text": message.text}
    )

    # Ограничиваем историю диалога
    if len(user_sessions[user_id]) > 10:
        # Сохраняем системный промпт, удаляем старые сообщения
        user_sessions[user_id] = [user_sessions[user_id][0]] + user_sessions[user_id][-9:]

    # Получаем ответ от модели
    response = get_yandex_gpt_response(user_sessions[user_id])

    # Добавляем ответ бота в историю
    user_sessions[user_id].append(
        {"role": "assistant", "text": response}
    )

    await message.answer(response)


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)