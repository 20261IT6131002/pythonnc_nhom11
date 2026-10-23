from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd


class AdminControllerMixin:
    def add_user(self, values):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            catalog.add_user(db, actor, values['username'], values['name'],
                             values['password'], values['role'])

    def toggle_user(self, row_id):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            catalog.toggle_user(db, actor, self._must(db, User, row_id))
