from io import BytesIO
import logging
import random
import re
from typing import Dict, Any, Optional

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
import cairosvg
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards import get_main_keyboard
from config import MASCOT_SVG_TEMPLATE_PATH
from models.database import get_session_ctx
from models.repository import (
    add_mascot as save_mascot,
    get_user_mascots,
    get_user_rating,
    get_top_users,
    get_user_position
)

# Импорт функций из скрипта generate_blin.py
from utils.generate_blin import (
    select_by_rarity, modify_svg_colors, replace_hat, load_svg,
    RARITY_WEIGHTS, COLOR_PALETTES, HAT_VARIANTS, HAT_COLORS
)

router = Router()

# Эмодзи для разных редкостей
RARITY_EMOJI = {
    "обычный": "⚪",
    "необычный": "🟢",
    "редкий": "🔵",
    "эпический": "🟣",
    "легендарный": "🟡"
}


@router.callback_query(F.data == "get_mascot")
async def generate_mascot(callback: CallbackQuery):
    """Генерация и отправка уникального маскота-блина"""
    await callback.message.answer("🎮 Генерирую уникального блина... Интересно, какая редкость выпадет?")

    try:
        # Загружаем базовый SVG
        svg_content = load_svg(MASCOT_SVG_TEMPLATE_PATH)

        # Изменяем фон на оранжевый FDBA74
        svg_content = re.sub(
            r'<rect width="227" height="227" fill="white"/>',
            r'<rect width="227" height="227" fill="#FDBA74"/>',
            svg_content
        )

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

        # Сохраняем маскота в базу данных
        user_id = callback.from_user.id
        async with await get_session_ctx() as session:
            mascot = await save_mascot(session, user_id, mascot_info)

        # Конвертируем SVG в PNG
        png_buffer = BytesIO()
        cairosvg.svg2png(bytestring=modified_svg, write_to=png_buffer, scale=2.0)
        png_buffer.seek(0)

        # Создаем файл для отправки
        input_file = BufferedInputFile(png_buffer.read(), filename="mascot.png")

        # Создаем описание маскота
        description = (
            f"<b>🎮 Поздравляем! Вы выбили блина!</b>\n\n"
            f"<b>👒 Шапка:</b> {hat_info['name']} {RARITY_EMOJI[hat_info['rarity']]} {hat_info['rarity'].capitalize()}\n"
            f"<b>🥞 Тело:</b> {RARITY_EMOJI[color_info['body']['rarity']]} {color_info['body']['rarity'].capitalize()}\n"
            f"<b>✏️ Обводка:</b> {RARITY_EMOJI[color_info['stroke']['rarity']]} {color_info['stroke']['rarity'].capitalize()}\n"
        )

        # Создаем кнопки
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="🎲 Выбить ещё блина", callback_data="get_mascot"))
        builder.add(types.InlineKeyboardButton(text="📚 Моя коллекция", callback_data="my_collection"))
        builder.add(types.InlineKeyboardButton(text="🏆 Мой рейтинг", callback_data="my_rating"))
        builder.add(types.InlineKeyboardButton(text="🏅 Топ игроков", callback_data="top_players"))
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

    async with await get_session_ctx() as session:
        # Получаем маскотов пользователя из БД
        mascots = await get_user_mascots(session, user_id)

        if not mascots:
            await callback.message.answer(
                "У вас пока нет ни одного блина в коллекции. Давайте выбьем первого!",
                reply_markup=InlineKeyboardBuilder().add(
                    types.InlineKeyboardButton(text="🎲 Выбить блина", callback_data="get_mascot")
                ).as_markup()
            )
            await callback.answer()
            return

        # Получаем рейтинг пользователя
        user_rating = await get_user_rating(session, user_id)

        # Статистика по коллекции
        collection_text = (
            f"<b>📚 Ваша коллекция блинов</b>\n\n"
            f"Всего блинов: <b>{len(mascots)}</b>\n\n"
            f"<b>Статистика редкости:</b>\n"
            f"⚪ Обычных: {user_rating['common_count']}\n"
            f"🟢 Необычных: {user_rating['uncommon_count']}\n"
            f"🔵 Редких: {user_rating['rare_count']}\n"
            f"🟣 Эпических: {user_rating['epic_count']}\n"
            f"🟡 Легендарных: {user_rating['legendary_count']}\n\n"
            f"<b>Текущий рейтинг:</b> {user_rating['rating_score']} очков\n"
            f"<b>Позиция в общем рейтинге:</b> {user_rating['rating_position']}"
        )

        # Создаем кнопки
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="🎲 Выбить ещё блина", callback_data="get_mascot"))
        builder.add(types.InlineKeyboardButton(text="🏆 Мой рейтинг", callback_data="my_rating"))
        builder.add(types.InlineKeyboardButton(text="🏅 Топ игроков", callback_data="top_players"))
        builder.add(types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"))
        builder.adjust(1)

        await callback.message.answer(collection_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "my_rating")
async def show_my_rating(callback: CallbackQuery):
    """Показывает рейтинг пользователя"""
    user_id = callback.from_user.id

    async with await get_session_ctx() as session:
        # Получаем рейтинг пользователя
        user_rating = await get_user_rating(session, user_id)

        if not user_rating:
            await callback.message.answer(
                "У вас пока нет рейтинга. Чтобы получить рейтинг, нужно выбить хотя бы одного блина!",
                reply_markup=InlineKeyboardBuilder().add(
                    types.InlineKeyboardButton(text="🎲 Выбить блина", callback_data="get_mascot")
                ).as_markup()
            )
            await callback.answer()
            return

        # Формируем сообщение о рейтинге
        username = user_rating["username"] or f"@{user_rating['user_id']}"
        full_name = user_rating["full_name"] or username

        rating_text = (
            f"<b>🏆 Рейтинг: {full_name}</b>\n\n"
            f"Всего блинов: <b>{user_rating['total_mascots']}</b>\n\n"
            f"<b>Детали коллекции:</b>\n"
            f"⚪ Обычных элементов: {user_rating['common_count']}\n"
            f"🟢 Необычных элементов: {user_rating['uncommon_count']}\n"
            f"🔵 Редких элементов: {user_rating['rare_count']}\n"
            f"🟣 Эпических элементов: {user_rating['epic_count']}\n"
            f"🟡 Легендарных элементов: {user_rating['legendary_count']}\n\n"
            f"<b>Ваш рейтинг:</b> {user_rating['rating_score']} очков\n"
            f"<b>Место в топе:</b> {user_rating['rating_position']}"
        )

        # Создаем кнопки
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="🎲 Выбить ещё блина", callback_data="get_mascot"))
        builder.add(types.InlineKeyboardButton(text="📚 Моя коллекция", callback_data="my_collection"))
        builder.add(types.InlineKeyboardButton(text="🏅 Топ игроков", callback_data="top_players"))
        builder.add(types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"))
        builder.adjust(1)

        await callback.message.answer(rating_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "top_players")
async def show_top_players(callback: CallbackQuery):
    """Показывает рейтинг топ игроков"""
    async with await get_session_ctx() as session:
        # Получаем топ-10 пользователей
        top_users = await get_top_users(session, limit=10)

        if not top_users:
            await callback.message.answer(
                "Рейтинг пока пуст! Будь первым, кто выбьет блина!",
                reply_markup=InlineKeyboardBuilder().add(
                    types.InlineKeyboardButton(text="🎲 Выбить блина", callback_data="get_mascot")
                ).as_markup()
            )
            await callback.answer()
            return

        # Формируем сообщение с топом
        top_text = "<b>🏅 Топ-10 игроков:</b>\n\n"

        medals = ["🥇", "🥈", "🥉"]
        for i, user in enumerate(top_users):
            position = i + 1
            medal = medals[i] if i < 3 else f"{position}."
            username = user["username"] or f"ID: {user['user_id']}"
            full_name = user["full_name"] or username

            top_text += (
                f"{medal} <b>{full_name}</b>\n"
                f"   ├ Рейтинг: {user['rating_score']} очков\n"
                f"   ├ Блинов: {user['total_mascots']}\n"
                f"   └ 🟡: {user['legendary_count']} | 🟣: {user['epic_count']} | "
                f"🔵: {user['rare_count']} | 🟢: {user['uncommon_count']} | ⚪: {user['common_count']}\n\n"
            )

        # Создаем кнопки
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="🎲 Выбить ещё блина", callback_data="get_mascot"))
        builder.add(types.InlineKeyboardButton(text="📚 Моя коллекция", callback_data="my_collection"))
        builder.add(types.InlineKeyboardButton(text="🏆 Мой рейтинг", callback_data="my_rating"))
        builder.add(types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"))
        builder.adjust(1)

        await callback.message.answer(top_text, reply_markup=builder.as_markup(), parse_mode="HTML")
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