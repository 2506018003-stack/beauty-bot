import logging
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select

from api.database import AsyncSessionLocal
from api.models import Booking, BookingStatus

logger = logging.getLogger(__name__)


async def send_visit_reminders(bot: Bot):
    """Reminds clients about confirmed bookings happening tomorrow."""
    tomorrow = (datetime.utcnow() + timedelta(days=1)).date()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Booking).where(
                Booking.booking_date == tomorrow,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.reminder_sent.is_(False),
            )
        )
        bookings = result.scalars().all()

        reminded = 0
        for booking in bookings:
            try:
                await bot.send_message(
                    booking.user_id,
                    f"⏰ <b>Напоминание</b>\n\n"
                    f"Завтра в {booking.booking_time.strftime('%H:%M')} у вас запись: "
                    f"{booking.service.name} к мастеру {booking.master.name}.\n\n"
                    f"Ждём вас!"
                )
                booking.reminder_sent = True
                session.add(booking)
                reminded += 1
            except Exception:
                logger.exception(f"Failed to send reminder for booking {booking.id}")

        await session.commit()

    if reminded:
        logger.info(f"Sent {reminded} visit reminders")
    return reminded
