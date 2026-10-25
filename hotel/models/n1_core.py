"""N1-owned reference data, staff records, and hotel settings.

The existing User.role column stays for backwards compatibility while
user_roles provides the explicit role relationship required by the project.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hotel.models.common import utc_now
from hotel.models.database import Base


class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class UserRole(Base):
    __tablename__ = 'user_roles'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'), primary_key=True)


class Employee(Base):
    __tablename__ = 'employees'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), default='', nullable=False)
    position: Mapped[str] = mapped_column(String(120), default='', nullable=False)


class SystemSetting(Base):
    __tablename__ = 'system_settings'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class EmailOtp(Base):
    """One-use email ownership proof; never stores the six-digit code."""
    __tablename__ = 'email_otps'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    purpose: Mapped[str] = mapped_column(String(24))
    code_digest: Mapped[str] = mapped_column(String(64))
    salt: Mapped[str] = mapped_column(String(32))
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CustomerLinkRequest(Base):
    """Manual verification before attaching a walk-in booking history to login."""
    __tablename__ = 'customer_link_requests'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), index=True)
    booking_code: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
