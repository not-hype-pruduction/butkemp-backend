from io import BytesIO
import logging
import random
import re
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
import cairosvg

from keyboards import get_main_keyboard
from utils.storage import user_mascots
from config import MASCOT_SVG_TEMPLATE_PATH

# Импорт функций из скрипта generate_blin.py
from utils.generate_blin import (
    select_by_rarity, modify_svg_colors, replace_hat, load_svg,
    RARITY_WEIGHTS, COLOR_PALETTES, HAT_VARIANTS, HAT_COLORS
)

router = Router()


@router.callback_query(F.data == "get_mascot")
async def generate_mascot(callback: CallbackQuery):
    """Генерация и отправка уникального маскота-блина"""
    await callback.message.answer("🎮 Генерирую уникального блина... Интересно, какая редкость выпадет?")

    try:
        # Загружаем базовый SVG
        svg_content = load_svg(MASCOT_SVG_TEMPLATE_PATH)

        # Модифицируем цвета
        modified_svg, color_info = modify_svg_colors(svg_content)

        # Выбираем редкость шапки
        hat_rarity = select_by_rarity()

        # Заменяем шапку специфическими цветами
        modified_svg, hat_info = replace_hat(modified_svg, hat_rarity)

        # Создаем инфо о маскоте
        mascot_info = {
            "hat": hat_info,
            "body": color_info["body"],
            "stroke": color_info["stroke"]
        }

        # Сохраняем маскота в хранилище пользователя
        user_id = callback.from_user.id
        if user_id not in user_mascots:
            user_mascots[user_id] = []
        user_mascots[user_id].append(mascot_info)

        # Конвертируем SVG в PNG
        png_buffer = BytesIO()
        cairosvg.svg2png(bytestring=modified_svg, write_to=png_buffer, scale=2.0)
        png_buffer.seek(0)

        # Создаем файл для отправки
        input_file = BufferedInputFile(png_buffer.read(), filename="mascot.png")

        # Создаем описание маскота
        rarity_emoji = {
            "обычный": "⚪",
            "необычный": "🟢",
            "редкий": "🔵",
            "эпический": "🟣",
            "легендарный": "🟡"
        }

        description = (
            f"<b>🎮 Поздравляем! Вы выбили блина!</b>\n\n"
            f"<b>👒 Шапка:</b> {hat_info['name']} {rarity_emoji[hat_info['rarity']]} {hat_info['rarity'].capitalize()}\n"
            f"<b>🥞 Тело:</b> {rarity_emoji[color_info['body']['rarity']]} {color_info['body']['rarity'].capitalize()}\n"
            f"<b>✏️ Обводка:</b> {rarity_emoji[color_info['stroke']['rarity']]} {color_info['stroke']['rarity'].capitalize()}\n"
        )

        # Создаем кнопки
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="🎲 Выбить ещё блина", callback_data="get_mascot"))
        builder.add(types.InlineKeyboardButton(text="📚 Моя коллекция", callback_data="my_collection"))
        builder.add(types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"))
        builder.adjust(1)

        # Отправляем PNG как фото
        await callback.message.answer_photo(
            photo=input_file,
            caption=description,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )

    except Exception as e:
        logging.error(f"Ошибка при генерации маскота: {e}")
        await callback.message.answer("К сожалению, произошла ошибка при генерации маскота. Попробуйте снова.")

    await callback.answer()

@router.callback_query(F.data == "my_collection")
async def show_collection(callback: CallbackQuery):
    """Показывает коллекцию маскотов пользователя"""
    user_id = callback.from_user.id

    if user_id not in user_mascots or not user_mascots[user_id]:
        await callback.message.answer(
            "У вас пока нет ни одного блина в коллекции. Давайте выбьем первого!",
            reply_markup=InlineKeyboardBuilder().add(
                types.InlineKeyboardButton(text="🎲 Выбить блина", callback_data="get_mascot")
            ).as_markup()
        )
        await callback.answer()
        return

    # Статистика по коллекции
    collection = user_mascots[user_id]
    stats = {rarity: 0 for rarity in RARITY_WEIGHTS.keys()}

    for mascot in collection:
        stats[mascot["hat"]["rarity"]] += 1
        stats[mascot["body"]["rarity"]] += 1
        stats[mascot["stroke"]["rarity"]] += 1

    # Создаем описание коллекции
    collection_text = (
        f"<b>📚 Ваша коллекция блинов</b>\n\n"
        f"Всего блинов: <b>{len(collection)}</b>\n\n"
        f"<b>Статистика редкости:</b>\n"
        f"⚪ Обычных: {stats['обычный']}\n"
        f"🟢 Необычных: {stats['необычный']}\n"
        f"🔵 Редких: {stats['редкий']}\n"
        f"🟣 Эпических: {stats['эпический']}\n"
        f"🟡 Легендарных: {stats['легендарный']}\n"
    )

    # Создаем кнопки
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🎲 Выбить ещё блина", callback_data="get_mascot"))
    builder.add(types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"))
    builder.adjust(1)

    await callback.message.answer(collection_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возвращает в главное меню"""
    await callback.message.answer(
        "Возвращаемся в главное меню:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)