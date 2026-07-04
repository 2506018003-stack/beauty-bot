from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from api.database import AsyncSessionLocal
from api.models import ServiceCategory, Service
from bot.keyboards.inline import service_categories_kb, services_kb

router = Router()


@router.message(F.text == "💅 Услуги")
async def list_categories(message: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ServiceCategory).order_by(ServiceCategory.sort_order))
        categories = result.scalars().all()

    if not categories:
        await message.answer("Каталог услуг пока не заполнен.")
        return

    await message.answer(
        "💅 <b>Выберите категорию:</b>",
        reply_markup=service_categories_kb([(c.id, c.name) for c in categories])
    )


@router.callback_query(F.data.startswith("svccat:"))
async def show_category_services(callback: CallbackQuery):
    cat_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Service).where(Service.category_id == cat_id, Service.is_active.is_(True))
        )
        services = result.scalars().all()

    if not services:
        await callback.answer("В этой категории пока пусто", show_alert=True)
        return

    for svc in services:
        text = f"<b>{svc.name}</b>\n{svc.description or ''}\n💰 {svc.price} ₽ · ⏱ {svc.duration_minutes} мин"
        if svc.photo_url:
            await callback.message.answer_photo(svc.photo_url, caption=text)
        else:
            await callback.message.answer(text)
    await callback.message.answer(
        "Готовы записаться? Нажмите «📅 Записаться» в меню и выберите нужную услугу."
    )
    await callback.answer()
