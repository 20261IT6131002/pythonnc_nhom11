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
    payments: Mapped[list['Payment']] = relationship(back_populates='invoice', cascade='all, delete-orphan')
    refunds: Mapped[list['Refund']] = relationship(back_populates='invoice')


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
    recorder: Mapped['User'] = relationship('User')


class BookingDeposit(Base):
    """Tiền đặt cọc của khách hàng khi đặt phòng trước khi lập hóa đơn."""
    __tablename__ = 'booking_deposits'
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    method: Mapped[str] = mapped_column(String(32), default='cash')  # cash, bank_transfer, card_manual
    reference: Mapped[str] = mapped_column(String(100), default='')
    status: Mapped[str] = mapped_column(String(20), default='paid')   # paid, applied, refunded, forfeited
    recorded_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    notes: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    booking: Mapped['Booking'] = relationship('Booking', back_populates='deposits')
    recorder: Mapped['User'] = relationship('User')
    refunds: Mapped[list['Refund']] = relationship('Refund', back_populates='deposit')


class Refund(Base):
    """Giao dịch hoàn tiền cho khách hàng (hoàn cọc, hủy phòng, trả thừa tiền)."""
    __tablename__ = 'refunds'
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'), index=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey('invoices.id'), nullable=True)
    deposit_id: Mapped[int | None] = mapped_column(ForeignKey('booking_deposits.id'), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    method: Mapped[str] = mapped_column(String(32), default='bank_transfer')  # cash, bank_transfer, card_manual
    reason: Mapped[str] = mapped_column(String(255), default='')
    status: Mapped[str] = mapped_column(String(20), default='completed')
    recorded_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    booking: Mapped['Booking'] = relationship('Booking', back_populates='refunds')
    invoice: Mapped['Invoice | None'] = relationship('Invoice', back_populates='refunds')
    deposit: Mapped['BookingDeposit | None'] = relationship('BookingDeposit', back_populates='refunds')
    recorder: Mapped['User'] = relationship('User')

