from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from bot.config import settings


def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="💅 Услуги"), KeyboardButton(text="🏠 Открыть приложение", web_app=WebAppInfo(url=settings.WEBAPP_URL))],
        [KeyboardButton(text="📅 Записаться"), KeyboardButton(text="🗓 Мои записи")],
        [KeyboardButton(text="⭐ Лояльность"), KeyboardButton(text="✍️ Отзывы")],
        [KeyboardButton(text="📞 Поддержка")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="🔧 Админ-панель", web_app=WebAppInfo(url=settings.CRM_URL))])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, input_field_placeholder="Выберите действие...")
