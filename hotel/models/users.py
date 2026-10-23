from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hotel.models.database import Base
from hotel.models.common import utc_now


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(250))
    role: Mapped[str] = mapped_column(String(25), default='receptionist')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
