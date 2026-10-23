from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hotel.models.database import Base
from hotel.models.common import utc_now


class Invoice(Base):
    __tablename__ = 'invoices'
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'), unique=True)
    room_amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    services_amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    booking: Mapped['Booking'] = relationship(back_populates='invoice')
    payments: Mapped[list['Payment']] = relationship(back_populates='invoice')

class Payment(Base):
    __tablename__ = 'payments'
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey('invoices.id'))
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    method: Mapped[str] = mapped_column(String(32))
    reference: Mapped[str] = mapped_column(String(100), default='')
    recorded_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    invoice: Mapped['Invoice'] = relationship(back_populates='payments')
