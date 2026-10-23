from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hotel.models.database import Base
from hotel.models.common import utc_now


class Booking(Base):
    __tablename__ = 'bookings'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'))
    room_id: Mapped[int] = mapped_column(ForeignKey('rooms.id'))
    checkin_date: Mapped[date] = mapped_column(Date)
    checkout_date: Mapped[date] = mapped_column(Date)
    guests: Mapped[int] = mapped_column(Integer, default=1)
    nightly_price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    notes: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    customer: Mapped['Customer'] = relationship()
    room: Mapped['Room'] = relationship()
    usages: Mapped[list['ServiceUsage']] = relationship(back_populates='booking')
    invoice: Mapped['Invoice | None'] = relationship(back_populates='booking', uselist=False)
