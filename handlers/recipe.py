import types

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import get_main_keyboard
from models.yandex_gpt import get_yandex_gpt_response

router = Router()

RECIPE_PROMPT = """Ты - креативный эксперт по кулинарии с хорошим чувством юмора.
Сгенерируй оригинальный забавный рецепт блинов с интересным названием. 
Твой ответ должен быть хорошо структурирован с использованием HTML-форматирования:

1. <b>КРЕАТИВНОЕ НАЗВАНИЕ РЕЦЕПТА</b> (используй эмодзи)
2. <i>Короткое забавное вступление (1-2 предложения)</i>
3. <b>Ингредиенты:</b> (список с маркерами • )
4. <b>Приготовление:</b> (пронумерованные шаги)
5. <b>Совет от шеф-повара:</b> (забавный неожиданный совет)
6. <i>Интересный факт о блинах</i> (что-то необычное и удивительное)

Добавь эмодзи для украшения текста. Пиши с юмором и живо!"""

@router.callback_query(F.data == "pancake_recipe")
async def send_pancake_recipe(callback: CallbackQuery):
    """Генерация и отправка рецепта блинов"""
    await callback.message.answer("🥞 Генерирую рецепт блинов... Подождите немного.")

    # Подготовка запроса к модели
    messages = [
        {"role": "system", "text": RECIPE_PROMPT},
        {"role": "user", "text": "Пожалуйста, придумай оригинальный забавный рецепт блинов."}
    ]

    # Получаем ответ от модели
    recipe = get_yandex_gpt_response(messages)

    # Создаем кнопку для возврата в меню
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"))
    builder.add(types.InlineKeyboardButton(text="🔄 Другой рецепт", callback_data="pancake_recipe"))
    builder.adjust(1)

    await callback.message.answer(
        recipe,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)