from datetime import datetime, timedelta, time as dtime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from api.database import AsyncSessionLocal
from api.models import Service, Master, Booking, BookingStatus, User
from bot.config import settings
from bot.states.states import BookingStates
from bot.keyboards.inline import services_kb, masters_kb, time_slots_kb, booking_confirm_kb
from bot.services.loyalty import add_points, award_first_visit_referral_bonus, points_earned_for_amount

router = Router()


def _slots_for_day() -> list[str]:
    slots = []
    t = dtime(9, 0)
    while t < dtime(20, 30):
        slots.append(t.strftime("%H:%M"))
        t = (datetime.combine(datetime.today(), t) + timedelta(minutes=30)).time()
    return slots


@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Service).where(Service.is_active.is_(True)))
        services = result.scalars().all()

    if not services:
        await message.answer("Пока нет доступных услуг для записи.")
        return

    await message.answer(
        "💅 <b>Выберите услугу:</b>",
        reply_markup=services_kb([(s.id, s.name, s.price) for s in services])
    )


@router.callback_query(F.data.startswith("svc:"))
async def choose_master(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    await state.update_data(service_id=service_id)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Master).where(Master.is_active.is_(True)))
        masters = result.scalars().all()

    if not masters:
        await callback.answer("Нет доступных мастеров", show_alert=True)
        return

    await callback.message.edit_text(
        "👤 <b>Выберите мастера:</b>",
        reply_markup=masters_kb([(m.id, m.name) for m in masters], service_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("master:"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    _, service_id, master_id = callback.data.split(":")
    await state.update_data(service_id=int(service_id), master_id=int(master_id))
    await state.set_state(BookingStates.date)
    await callback.message.edit_text(
        "📅 Введите дату (ДД.ММ.ГГГГ) или напишите «сегодня»/«завтра»:"
    )
    await callback.answer()


@router.message(BookingStates.date)
async def set_date(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text == "сегодня":
        date_ = datetime.today().date()
    elif text == "завтра":
        date_ = (datetime.today() + timedelta(days=1)).date()
    else:
        try:
            date_ = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await message.answer("❌ Не понял дату. Формат: ДД.ММ.ГГГГ, либо «сегодня»/«завтра»")
            return

    await state.update_data(booking_date=date_.isoformat())
    await state.set_state(BookingStates.time)
    await message.answer(f"⏰ Выберите время ({settings.OPEN_HOURS}):", reply_markup=time_slots_kb(_slots_for_day()))


@router.callback_query(BookingStates.time, F.data.startswith("time:"))
async def set_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split(":", 1)[1]
    await state.update_data(booking_time=time_str)
    await state.set_state(BookingStates.comment)
    await callback.message.edit_text("💬 Пожелания к визиту? (или напишите «нет»)")
    await callback.answer()


@router.message(BookingStates.comment)
async def set_comment(message: Message, state: FSMContext):
    comment = "" if message.text.strip().lower() == "нет" else message.text.strip()
    await state.update_data(comment=comment)
    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        svc_result = await session.execute(select(Service).where(Service.id == data["service_id"]))
        service = svc_result.scalar_one()
        master_result = await session.execute(select(Master).where(Master.id == data["master_id"]))
        master = master_result.scalar_one()

    await state.set_state(BookingStates.confirm)
    await message.answer(
        f"📋 <b>Проверьте запись:</b>\n\n"
        f"💅 Услуга: {service.name} ({service.price} ₽, {service.duration_minutes} мин)\n"
        f"👤 Мастер: {master.name}\n"
        f"📅 Дата: {data['booking_date']}\n"
        f"⏰ Время: {data['booking_time']}\n"
        f"💬 {comment or '—'}",
        reply_markup=booking_confirm_kb()
    )


@router.callback_query(BookingStates.confirm, F.data == "booking:confirm")
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        service_result = await session.execute(select(Service).where(Service.id == data["service_id"]))
        service = service_result.scalar_one()

        booking = Booking(
            user_id=callback.from_user.id,
            master_id=data["master_id"],
            service_id=data["service_id"],
            booking_date=datetime.fromisoformat(data["booking_date"]).date(),
            booking_time=datetime.strptime(data["booking_time"], "%H:%M").time(),
            comment=data.get("comment", ""),
            status=BookingStatus.PENDING,
            points_earned=points_earned_for_amount(service.price),
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)

    await callback.message.edit_text(f"✅ Заявка на запись #{booking.id} отправлена! Мы подтвердим её в ближайшее время.")
    await state.clear()

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"admbook:confirm:{booking.id}")
    kb.button(text="❌ Отклонить", callback_data=f"admbook:decline:{booking.id}")
    kb.adjust(2)
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 <b>Новая запись #{booking.id}</b>\n"
                f"👤 {callback.from_user.full_name} (@{callback.from_user.username or '-'})\n"
                f"💅 {service.name}\n"
                f"📅 {data['booking_date']} ⏰ {data['booking_time']}\n"
                f"💬 {data.get('comment') or '—'}",
                reply_markup=kb.as_markup()
            )
        except Exception:
            pass
    await callback.answer()


@router.callback_query(BookingStates.confirm, F.data == "booking:cancel")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Запись отменена.")
    await callback.answer()


@router.callback_query(F.data.startswith("admbook:"))
async def admin_booking_action(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, action, booking_id = callback.data.split(":")
    booking_id = int(booking_id)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Booking).where(Booking.id == booking_id))
        booking = result.scalar_one_or_none()
        if not booking:
            await callback.answer("Запись не найдена", show_alert=True)
            return

        if action == "confirm":
            booking.status = BookingStatus.CONFIRMED
            label = "подтверждена ✅"
        elif action == "decline":
            booking.status = BookingStatus.CANCELLED
            label = "отклонена ❌"
        elif action == "done":
            booking.status = BookingStatus.DONE
            label = "выполнена 🎉"
            await add_points(session, booking.user_id, booking.points_earned, f"booking_{booking.id}_visit")
            user_result = await session.execute(select(User).where(User.id == booking.user_id))
            user = user_result.scalar_one()
            await award_first_visit_referral_bonus(session, user)
        else:
            await callback.answer()
            return

        session.add(booking)
        await session.commit()
        guest_id = booking.user_id

    await callback.message.edit_text(callback.message.text + f"\n\nСтатус: {label}")

    if action == "confirm":
        kb = InlineKeyboardBuilder()
        kb.button(text="🎉 Отметить как выполнено", callback_data=f"admbook:done:{booking_id}")
        try:
            await callback.message.answer("После визита не забудьте отметить запись выполненной:", reply_markup=kb.as_markup())
        except Exception:
            pass

    try:
        if action == "done":
            await bot.send_message(guest_id, f"🎉 Спасибо за визит! Начислено баллов: {booking.points_earned}")
        else:
            await bot.send_message(guest_id, f"💅 Ваша запись #{booking_id} {label}")
    except Exception:
        pass
    await callback.answer()


@router.message(F.text == "🗓 Мои записи")
async def my_bookings(message: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Booking).where(Booking.user_id == message.from_user.id).order_by(Booking.created_at.desc()).limit(10)
        )
        bookings = result.scalars().all()

    if not bookings:
        await message.answer("У вас пока нет записей.")
        return

    lines = ["🗓 <b>Ваши записи:</b>\n"]
    for b in bookings:
        lines.append(f"#{b.id} — {b.service.name} · {b.booking_date} {b.booking_time.strftime('%H:%M')} · {b.status.value}")
    await message.answer("\n".join(lines))
