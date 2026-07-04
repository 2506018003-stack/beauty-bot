from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Date, Time,
    ForeignKey, Enum, Boolean, Text, BigInteger, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from api.database import Base


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DONE = "done"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    phone = Column(String(50))
    lang = Column(String(10), default="ru")
    loyalty_points = Column(Integer, default=0, nullable=False)
    referral_code = Column(String(20), unique=True, index=True)
    referred_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    bookings = relationship("Booking", back_populates="user", lazy="selectin")

    __table_args__ = (
        CheckConstraint('loyalty_points >= 0', name='check_points_non_negative'),
    )


class Master(Base):
    __tablename__ = "masters"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    specialty = Column(String(255))
    photo_url = Column(String(500))
    bio = Column(Text)
    is_active = Column(Boolean, default=True, index=True)

    bookings = relationship("Booking", back_populates="master", lazy="selectin")


class ServiceCategory(Base):
    __tablename__ = "service_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    sort_order = Column(Integer, default=0)
    services = relationship("Service", back_populates="category", lazy="selectin")


class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    photo_url = Column(String(500))
    category_id = Column(Integer, ForeignKey("service_categories.id"))
    category = relationship("ServiceCategory", back_populates="services")
    is_active = Column(Boolean, default=True, index=True)


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    master_id = Column(Integer, ForeignKey("masters.id"), index=True)
    service_id = Column(Integer, ForeignKey("services.id"), index=True)
    booking_date = Column(Date, nullable=False, index=True)
    booking_time = Column(Time, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, index=True)
    comment = Column(Text)
    points_earned = Column(Integer, default=0)
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="bookings")
    master = relationship("Master", back_populates="bookings", lazy="joined")
    service = relationship("Service", lazy="joined")


class LoyaltyLedger(Base):
    __tablename__ = "loyalty_ledger"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    delta = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ReferralBonus(Base):
    __tablename__ = "referral_bonuses"
    id = Column(Integer, primary_key=True)
    referrer_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    referred_id = Column(BigInteger, ForeignKey("users.id"), index=True, unique=True)
    bonus_points = Column(Integer, default=0)
    awarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    master_id = Column(Integer, ForeignKey("masters.id"), nullable=True, index=True)
    rating = Column(Integer, nullable=False)
    text = Column(Text)
    is_published = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    master = relationship("Master", lazy="joined")

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )
