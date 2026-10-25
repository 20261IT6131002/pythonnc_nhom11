from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd
from hotel.services import customer_accounts
from hotel.services.phone import phones_match


class CustomersControllerMixin:
    def customer_history(self):
        with self._session() as db:
            return customer_accounts.history(db, self._require_user(db))

    def request_customer_link(self, booking_code, phone):
        with self._session() as db:
            return customer_accounts.request_link(db, self._require_user(db), booking_code, phone)

    def find_customers_by_phone(self, phone):
        with self._session() as db:
            self._require_staff(db)
            rows = db.scalars(select(Customer).order_by(Customer.id.desc()).limit(2000)).all()
            return [{'id': x.id, 'name': x.full_name, 'phone': x.phone,
                     'email': x.email, 'linked': x.user_id is not None}
                    for x in rows if phones_match(x.phone, phone)][:20]

    def link_requests(self):
        with self._session() as db:
            self._require_staff(db, admin=True)
            return customer_accounts.pending_requests(db)

    def decide_customer_link(self, row_id, approve):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            customer_accounts.decide_link(db, actor, row_id, approve)

    def save_customer(self, values, row_id=None):
        with self._session() as db:
            actor = self._require_staff(db)
            catalog.save_customer(db, actor, self._must(db, Customer, row_id) if row_id else None,
                                  values['name'], values['phone'], values.get('email', ''),
                                  values.get('document_no', ''))
