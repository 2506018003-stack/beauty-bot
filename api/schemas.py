from pydantic import BaseModel
from datetime import date, time, datetime
from decimal import Decimal


class BookingCreate(BaseModel):
    service_id: int
    master_id: int
    booking_date: date
    booking_time: time
    comment: str = ""


class BookingStatusUpdate(BaseModel):
    status: str


class ReviewOut(BaseModel):
    id: int
    rating: int
    text: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
