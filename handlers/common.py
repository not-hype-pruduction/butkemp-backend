from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards import get_main_keyboard
from utils.storage import psychologist_active

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    await message.answer(
        "👋 Добро пожаловать! Я бот для профориентации и карьерной консультации.\n\n"
        "Что я умею:\n"
        "• 🧭 Помогу с карьерными вопросами\n"
        "• 🎓 Предложу материалы по профориентации\n"
        "• 🧩 Проведу тест на определение склонностей\n"
        "• 🥞 Расскажу как приготовить блины (в качестве бонуса)",
        reply_markup=get_main_keyboard(is_career_assistant_active=False)
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help"""
    await message.answer(
        "🔍 <b>Доступные команды:</b>\n\n"
        "/start - Начать взаимодействие с ботом\n"
        "/help - Показать справку\n"
        "/menu - Открыть главное меню\n\n"
        "Используйте кнопки меню для навигации по функциям бота.",
        reply_markup=get_main_keyboard(is_career_assistant_active=psychologist_active.get(message.from_user.id, False))
    )

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Показать главное меню"""
    await message.answer(
        "📋 Главное меню. Выберите раздел:",
        reply_markup=get_main_keyboard(is_career_assistant_active=psychologist_active.get(message.from_user.id, False))
    )

def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)