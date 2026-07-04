from fastapi import APIRouter, Depends
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from api.database import get_db
from api.models import Booking, BookingStatus, Review, Master, Service
from api.schemas import BookingStatusUpdate
from api.dependencies import verify_admin_token
from bot.services.loyalty import add_points, award_first_visit_referral_bonus

router = APIRouter()


@router.get("/bookings")
async def get_bookings(days: int = 30, db: AsyncSession = Depends(get_db), admin=Depends(verify_admin_token)):
    result = await db.execute(
        select(Booking).where(Booking.created_at >= datetime.utcnow() - timedelta(days=days))
        .order_by(Booking.created_at.desc()).limit(200)
    )
    bookings = result.scalars().all()
    return [
        {
            "id": b.id, "user_id": b.user_id, "service": b.service.name, "master": b.master.name,
            "booking_date": str(b.booking_date), "booking_time": str(b.booking_time),
            "comment": b.comment, "status": b.status.value, "created_at": str(b.created_at),
            "points_earned": b.points_earned
        }
        for b in bookings
    ]


@router.patch("/bookings/{booking_id}/status")
async def update_booking_status(booking_id: int, payload: BookingStatusUpdate, db: AsyncSession = Depends(get_db), admin=Depends(verify_admin_token)):
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one()
    booking.status = payload.status
    db.add(booking)

    if payload.status == BookingStatus.DONE.value:
        await add_points(db, booking.user_id, booking.points_earned, f"booking_{booking.id}_visit")
        from api.models import User
        user_result = await db.execute(select(User).where(User.id == booking.user_id))
        user = user_result.scalar_one()
        await award_first_visit_referral_bonus(db, user)

    await db.commit()
    return {"status": "updated", "booking_id": booking_id}


@router.get("/masters")
async def get_masters(db: AsyncSession = Depends(get_db), admin=Depends(verify_admin_token)):
    result = await db.execute(select(Master))
    return [
        {"id": m.id, "name": m.name, "specialty": m.specialty, "is_active": m.is_active}
        for m in result.scalars().all()
    ]


@router.get("/reviews")
async def get_reviews(db: AsyncSession = Depends(get_db), admin=Depends(verify_admin_token)):
    result = await db.execute(select(Review).order_by(Review.created_at.desc()).limit(100))
    return [
        {
            "id": r.id, "user_id": r.user_id, "rating": r.rating, "text": r.text,
            "master": r.master.name if r.master else None, "created_at": str(r.created_at)
        }
        for r in result.scalars().all()
    ]


@router.get("/dashboard")
async def dashboard_stats(db: AsyncSession = Depends(get_db), admin=Depends(verify_admin_token)):
    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)

    pending_bookings = await db.execute(
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.PENDING)
    )
    today_bookings = await db.execute(
        select(func.count(Booking.id)).where(Booking.booking_date == today)
    )
    week_revenue = await db.execute(
        select(func.sum(Service.price)).select_from(Booking)
        .join(Service, Service.id == Booking.service_id)
        .where(Booking.status == BookingStatus.DONE, Booking.created_at >= week_ago)
    )
    avg_rating = await db.execute(select(func.avg(Review.rating)))

    top_masters_result = await db.execute(
        select(Master.name, func.count(Booking.id).label("cnt"))
        .join(Booking, Booking.master_id == Master.id)
        .where(Booking.status == BookingStatus.DONE)
        .group_by(Master.name).order_by(func.count(Booking.id).desc()).limit(5)
    )

    top_services_result = await db.execute(
        select(Service.name, func.count(Booking.id).label("cnt"))
        .join(Booking, Booking.service_id == Service.id)
        .where(Booking.status == BookingStatus.DONE)
        .group_by(Service.name).order_by(func.count(Booking.id).desc()).limit(5)
    )

    return {
        "pending_bookings": pending_bookings.scalar() or 0,
        "today_bookings": today_bookings.scalar() or 0,
        "week_revenue": float(week_revenue.scalar() or 0),
        "avg_rating": round(float(avg_rating.scalar() or 0), 1),
        "top_masters": [{"name": n, "count": c} for n, c in top_masters_result.all()],
        "top_services": [{"name": n, "count": c} for n, c in top_services_result.all()],
    }
