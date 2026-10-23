from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hotel.models.database import Base
from hotel.models.common import utc_now


class RoomType(Base):
    __tablename__ = 'room_types'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, default='')
    capacity: Mapped[int] = mapped_column(Integer, default=2)
    nightly_price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    rooms: Mapped[list['Room']] = relationship(back_populates='room_type')

class Room(Base):
    __tablename__ = 'rooms'
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    floor: Mapped[int] = mapped_column(Integer, default=1)
    room_type_id: Mapped[int] = mapped_column(ForeignKey('room_types.id'))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    room_type: Mapped['RoomType'] = relationship(back_populates='rooms')
