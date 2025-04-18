from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import get_main_keyboard
from utils.storage import professions, current_lecture, lectures
from data.professions import PROFESSIONS_LECTURES, PROFESSION_DESCRIPTIONS

router = Router()


@router.callback_query(F.data == "career_guidance")
async def career_guidance_menu(callback: CallbackQuery):
    """Показать меню профориентации"""
    # Создаем клавиатуру с доступными профессиями
    builder = InlineKeyboardBuilder()

    for profession in PROFESSIONS_LECTURES.keys():
        builder.add(F.text(profession, callback_data=f"profession_{profession}"))

    builder.add(F.text("⬅️ Назад", callback_data="back_to_menu"))
    builder.adjust(1)  # По одной кнопке в строке

    await callback.message.answer(
        "🎓 <b>Профориентация</b>\n\n"
        "Выберите интересующую вас профессию, чтобы узнать о ней больше и получить доступ к лекциям:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("profession_"))
async def show_profession_info(callback: CallbackQuery):
    """Показать информацию о выбранной профессии"""
    user_id = callback.from_user.id
    profession = callback.data.replace("profession_", "")

    # Сохраняем выбранную профессию
    professions[user_id] = profession

    # Создаем клавиатуру с доступными лекциями
    builder = InlineKeyboardBuilder()

    for i, lecture in enumerate(PROFESSIONS_LECTURES[profession]):
        builder.add(F.text(f"📚 {lecture}", callback_data=f"lecture_{i}"))

    builder.add(F.text("⬅️ Назад к профессиям", callback_data="career_guidance"))
    builder.add(F.text("🏠 В главное меню", callback_data="back_to_menu"))
    builder.adjust(1)  # По одной кнопке в строке

    await callback.message.answer(
        f"🎯 <b>Профессия: {profession}</b>\n\n"
        f"{PROFESSION_DESCRIPTIONS[profession]}\n\n"
        f"Выберите лекцию, чтобы узнать больше:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("lecture_"))
async def show_lecture(callback: CallbackQuery):
    """Показать выбранную лекцию"""
    user_id = callback.from_user.id
    lecture_index = int(callback.data.replace("lecture_", ""))

    if user_id not in professions:
        # Если пользователь попал сюда необычным путем
        await callback.answer("Произошла ошибка. Вернитесь в главное меню.")
        return

    profession = professions[user_id]
    lecture_name = PROFESSIONS_LECTURES[profession][lecture_index]

    # Сохраняем текущую лекцию
    lectures[user_id] = lecture_name
    current_lecture[user_id] = lecture_index

    # Здесь должно быть содержание лекции
    # Для примера генерируем простой текст
    lecture_content = f"<b>{lecture_name}</b>\n\n"
    lecture_content += f"Это лекция о профессии '{profession}'. В реальном боте здесь будет подробная информация, "
    lecture_content += f"образовательные материалы, ссылки на полезные ресурсы и рекомендации по обучению.\n\n"

    # Создаем кнопки навигации
    builder = InlineKeyboardBuilder()

    # Кнопки перехода между лекциями
    if lecture_index > 0:
        builder.add(F.text("⬅️ Предыдущая", callback_data=f"lecture_{lecture_index - 1}"))

    if lecture_index < len(PROFESSIONS_LECTURES[profession]) - 1:
        builder.add(F.text("➡️ Следующая", callback_data=f"lecture_{lecture_index + 1}"))

    builder.add(F.text("⬅️ К списку лекций", callback_data=f"profession_{profession}"))
    builder.add(F.text("🏠 В главное меню", callback_data="back_to_menu"))
    builder.adjust(2, 1, 1)  # Форматируем кнопки

    await callback.message.answer(lecture_content, reply_markup=builder.as_markup())
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)