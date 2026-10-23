from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd


class ServicesControllerMixin:
    def save_service(self, values, row_id=None):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            catalog.save_service(db, actor, self._must(db, HotelService, row_id) if row_id else None,
                                 values['name'], values['price'], values.get('active', True))

    def add_usage(self, booking_id, service_id, quantity):
        with self._session() as db:
            actor = self._require_staff(db)
            business.add_service_usage(db, self._must(db, Booking, booking_id),
                self._must(db, HotelService, service_id), catalog.positive_int(quantity, 1, 1000), actor)
