from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd


class CustomersControllerMixin:
    def save_customer(self, values, row_id=None):
        with self._session() as db:
            actor = self._require_staff(db)
            catalog.save_customer(db, actor, self._must(db, Customer, row_id) if row_id else None,
                                  values['name'], values['phone'], values.get('email', ''),
                                  values.get('document_no', ''))
