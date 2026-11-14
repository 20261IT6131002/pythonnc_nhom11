"""Additive N3 tables sharing the application's existing SQLAlchemy registry."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hotel.models.common import utc_now
from hotel.models.database import Base


class CustomerProfile(Base):
    __tablename__ = 'customer_profiles'

    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), primary_key=True)
    category: Mapped[str] = mapped_column(String(20), default='normal')
    address: Mapped[str] = mapped_column(String(250), default='')
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    organization: Mapped[str] = mapped_column(String(160), default='')
    preferences: Mapped[str] = mapped_column(Text, default='')
    special_requests: Mapped[str] = mapped_column(Text, default='')


class BookingGuest(Base):
    __tablename__ = 'booking_guests'

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'), index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    document_no: Mapped[str] = mapped_column(String(70), default='')
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str] = mapped_column(String(80), default='Việt Nam')
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class ServiceDetails(Base):
    __tablename__ = 'service_details'
    __table_args__ = (CheckConstraint('slot_capacity >= 1'), CheckConstraint('duration_minutes >= 1'))

    service_id: Mapped[int] = mapped_column(ForeignKey('hotel_services.id'), primary_key=True)
    category: Mapped[str] = mapped_column(String(80), default='Tiện ích')
    unit: Mapped[str] = mapped_column(String(40), default='lượt')
    description: Mapped[str] = mapped_column(String(500), default='')
    requires_schedule: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    slot_capacity: Mapped[int] = mapped_column(Integer, default=1)


class ServiceOrder(Base):
    __tablename__ = 'service_orders'
    __table_args__ = (CheckConstraint('quantity >= 1 AND quantity <= 1000'),
                      CheckConstraint('unit_price >= 0'))

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey('hotel_services.id'), index=True)
    service_name: Mapped[str] = mapped_column(String(130))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(String(500), default='')
    requested_by: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    usage_id: Mapped[int | None] = mapped_column(ForeignKey('service_usages.id'), unique=True, nullable=True)
    request_token: Mapped[str] = mapped_column(String(64), unique=True)


class Promotion(Base):
    __tablename__ = 'promotions'
    __table_args__ = (CheckConstraint('value > 0'), CheckConstraint('usage_limit >= 1'),
                      CheckConstraint('used_count >= 0'))

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    discount_type: Mapped[str] = mapped_column(String(20))
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    minimum_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    usage_limit: Mapped[int] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class BookingPromotion(Base):
    __tablename__ = 'booking_promotions'

    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'), primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey('promotions.id'), index=True)
    code: Mapped[str] = mapped_column(String(32))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    applied_by: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class InvoiceCustomerSnapshot(Base):
    __tablename__ = 'invoice_customer_snapshots'

    invoice_id: Mapped[int] = mapped_column(ForeignKey('invoices.id'), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(25))
    email: Mapped[str] = mapped_column(String(160), default='')
    document_no: Mapped[str] = mapped_column(String(70), default='')
