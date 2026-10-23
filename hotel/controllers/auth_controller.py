from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd


class AuthControllerMixin:
    def login(self, username, password):
        with self._session() as db:
            u = db.scalar(select(User).where(User.username == str(username).strip()))
            if not u or not u.active or not verify_password(password, u.password_hash):
                raise ValueError('Sai tài khoản/mật khẩu hoặc tài khoản bị khóa.')
            self.user = {'id': u.id, 'name': u.full_name, 'role': u.role}
            return dict(self.user)

    def logout(self):
        self.user = None
