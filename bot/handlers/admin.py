import asyncio
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func

from api.database import AsyncSessionLocal
from api.models import User, Booking, BookingStatus
from bot.config import settings
from bot.states.states import AdminStates

router = Router()


@router.message(F.text == "🔧 Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        return
    await message.answer(
        "🔧 <b>Админ-команды</b>\n\n"
        "<code>/broadcast</code> — рассылка всем клиентам\n"
        "<code>/stats</code> — статистика\n\n"
        f"CRM: {settings.CRM_URL}"
    )


@router.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        return
    today = datetime.utcnow().date()
    async with AsyncSessionLocal() as session:
        users_count = await session.execute(select(func.count(User.id)))
        new_bookings = await session.execute(
            select(func.count(Booking.id)).where(func.date(Booking.created_at) == today, Booking.status == BookingStatus.PENDING)
        )
        done_bookings = await session.execute(
            select(func.count(Booking.id)).where(Booking.status == BookingStatus.DONE)
        )
        revenue = await session.execute(
            select(func.sum(Booking.points_earned)).where(Booking.status == BookingStatus.DONE)
        )

    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Всего клиентов: {users_count.scalar() or 0}\n"
        f"🆕 Новые записи сегодня: {new_bookings.scalar() or 0}\n"
        f"✅ Визитов выполнено: {done_bookings.scalar() or 0}\n"
        f"⭐ Баллов начислено всего: {revenue.scalar() or 0}\n\n"
        f"Полный дашборд: {settings.CRM_URL}"
    )


@router.message(Command("broadcast"))
async def broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id not in settings.ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer("✍️ Пришлите текст рассылки (следующим сообщением):")


@router.message(AdminStates.waiting_broadcast)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    text = message.text or message.caption or ""

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.id))
        user_ids = [row[0] for row in result.all()]

    sent, failed = 0, 0
    status_msg = await message.answer(f"📤 Рассылка начата: 0/{len(user_ids)}")
    for i, uid in enumerate(user_ids):
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
        if i % 20 == 0:
            try:
                await status_msg.edit_text(f"📤 Рассылка: {i+1}/{len(user_ids)}")
            except Exception:
                pass

    await status_msg.edit_text(f"✅ Рассылка завершена: отправлено {sent}, ошибок {failed}")
