import types

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import get_main_keyboard
from models.yandex_gpt import get_yandex_gpt_response

router = Router()

RECIPE_PROMPT = """Ты - эксперт по кулинарии.
Сгенерируй оригинальный рецепт блинов. Рецепт должен включать список ингредиентов и пошаговую инструкцию приготовления.
Добавь интересный факт о блинах в конце."""


@router.callback_query(F.data == "pancake_recipe")
async def send_pancake_recipe(callback: CallbackQuery):
    """Генерация и отправка рецепта блинов"""
    await callback.message.answer("🥞 Генерирую рецепт блинов... Подождите немного.")

    # Подготовка запроса к модели
    messages = [
        {"role": "system", "text": RECIPE_PROMPT},
        {"role": "user", "text": "Пожалуйста, придумай оригинальный рецепт блинов."}
    ]

    # Получаем ответ от модели
    recipe = get_yandex_gpt_response(messages)

    # Создаем кнопку для возврата в меню
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"))
    builder.add(types.InlineKeyboardButton(text="🔄 Другой рецепт", callback_data="pancake_recipe"))
    builder.adjust(1)

    await callback.message.answer(
        f"<b>🥞 Рецепт блинов</b>\n\n{recipe}",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)