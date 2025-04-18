from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from utils.storage import psychologist_active
from data.professions import PROFESSIONS_LECTURES

def get_main_keyboard(is_career_assistant_active=False):
    """Создает основную клавиатуру бота"""
    builder = InlineKeyboardBuilder()

    # Кнопка карьерного ассистента
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

    # Кнопка для получения рецепта блинов
    builder.add(types.InlineKeyboardButton(
        text="🥞 Получить рецепт блинов",
        callback_data="pancake_recipe"
    ))

    # Кнопка режима профориентации
    builder.add(types.InlineKeyboardButton(
        text="🎓 Профориентация",
        callback_data="career_guidance"
    ))

    # Кнопка теста
    builder.add(types.InlineKeyboardButton(
        text="🧩 Профориентационный тест",
        callback_data="career_test"
    ))

    # Выравниваем кнопки по 1 в ряду
    builder.adjust(1)
    return builder.as_markup()

# Другие функции клавиатур...