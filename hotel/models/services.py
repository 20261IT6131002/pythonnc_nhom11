from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hotel.models.database import Base
from hotel.models.common import utc_now


class HotelService(Base):
    __tablename__ = 'hotel_services'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(130), unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class ServiceUsage(Base):
    __tablename__ = 'service_usages'
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'))
    service_id: Mapped[int] = mapped_column(ForeignKey('hotel_services.id'))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    booking: Mapped['Booking'] = relationship(back_populates='usages')
    service: Mapped['HotelService'] = relationship()
