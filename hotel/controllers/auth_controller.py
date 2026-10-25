from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services import auth
from hotel.controllers.utils import vnd


class AuthControllerMixin:
    def login(self, username, password):
        self.user = None
        with self._session() as db:
            self.user = auth.authenticate(db, username, password)
            return dict(self.user)

    def request_registration_otp(self, email):
        with self._session() as db:
            auth.request_registration_otp(db, email)

    def register_customer(self, username, name, email, password, confirmation, otp, phone):
        with self._session() as db:
            auth.register_customer(db, username, name, email, password, confirmation, otp, phone)

    def request_password_reset(self, email):
        with self._session() as db:
            return auth.request_password_reset(db, email)

    def reset_password_with_otp(self, email, code, password, confirmation):
        with self._session() as db:
            auth.reset_password_with_otp(db, email, code, password, confirmation)

    def request_link_email(self, current_password, email):
        with self._session() as db:
            auth.request_link_email(db, self._require_user(db), current_password, email)

    def confirm_link_email(self, email, code):
        with self._session() as db:
            auth.confirm_link_email(db, self._require_user(db), email, code)

    def change_password(self, old_password, new_password, confirmation):
        with self._session() as db:
            new_tag = auth.change_password(db, self._require_user(db), old_password,
                                           new_password, confirmation)
            self.user['_credential_tag'] = new_tag

    def set_customer_phone(self, password, phone):
        with self._session() as db:
            auth.set_customer_phone(db, self._require_user(db), password, phone)
            self.user['phone'] = db.get(User, self.user['id']).phone

    def get_current_user(self):
        with self._session() as db:
            user = self._require_user(db)
            return {'id': user.id, 'name': user.full_name, 'role': user.role,
                    'email': user.email, 'phone': user.phone,
                    'email_verified': user.email_verified_at is not None,
                    'requires_password_change': bool(user.must_change_password)}

    def logout(self):
        self.user = None
