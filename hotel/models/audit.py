from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hotel.models.database import Base
from hotel.models.common import utc_now


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[str] = mapped_column(String(300), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
