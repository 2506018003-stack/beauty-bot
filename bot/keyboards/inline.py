from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def service_categories_kb(categories: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for cat_id, name in categories:
        b.button(text=name, callback_data=f"svccat:{cat_id}")
    b.adjust(2)
    return b.as_markup()


def services_kb(services: list[tuple[int, str, str]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for svc_id, name, price in services:
        b.button(text=f"{name} — {price} ₽", callback_data=f"svc:{svc_id}")
    b.adjust(1)
    return b.as_markup()


def masters_kb(masters: list[tuple[int, str]], service_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for m_id, name in masters:
        b.button(text=name, callback_data=f"master:{service_id}:{m_id}")
    b.adjust(1)
    return b.as_markup()


def time_slots_kb(slots: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in slots:
        b.button(text=s, callback_data=f"time:{s}")
    b.adjust(4)
    return b.as_markup()


def booking_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Подтвердить запись", callback_data="booking:confirm")
    b.button(text="❌ Отменить", callback_data="booking:cancel")
    b.adjust(1)
    return b.as_markup()


def rating_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for n in range(1, 6):
        b.button(text="⭐" * n, callback_data=f"rating:{n}")
    b.adjust(1)
    return b.as_markup()
