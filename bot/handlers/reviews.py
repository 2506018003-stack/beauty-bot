from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from api.database import AsyncSessionLocal
from api.models import Review, Master
from bot.states.states import ReviewStates
from bot.keyboards.inline import rating_kb

router = Router()


@router.message(F.text == "✍️ Отзывы")
async def start_review(message: Message, state: FSMContext):
    await state.set_state(ReviewStates.rating)
    await message.answer("⭐ Оцените ваш визит:", reply_markup=rating_kb())


@router.callback_query(ReviewStates.rating, F.data.startswith("rating:"))
async def set_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":")[1])
    await state.update_data(rating=rating)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Master).where(Master.is_active.is_(True)))
        masters = result.scalars().all()

    kb = InlineKeyboardBuilder()
    for m in masters:
        kb.button(text=m.name, callback_data=f"review_master:{m.id}")
    kb.button(text="Без указания мастера", callback_data="review_master:0")
    kb.adjust(1)

    await callback.message.edit_text(f"Оценка: {'⭐' * rating}\n\n👤 О каком мастере отзыв?", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("review_master:"))
async def set_master(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split(":")[1])
    await state.update_data(master_id=master_id or None)
    await state.set_state(ReviewStates.text)
    await callback.message.edit_text("💬 Напишите отзыв текстом (или «нет»):")
    await callback.answer()


@router.message(ReviewStates.text)
async def set_text(message: Message, state: FSMContext):
    data = await state.get_data()
    text = "" if message.text.strip().lower() == "нет" else message.text.strip()

    async with AsyncSessionLocal() as session:
        session.add(Review(
            user_id=message.from_user.id,
            master_id=data.get("master_id"),
            rating=data["rating"],
            text=text
        ))
        await session.commit()

    await state.clear()
    await message.answer("🙏 Спасибо за отзыв!")
