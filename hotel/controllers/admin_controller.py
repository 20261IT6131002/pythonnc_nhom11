from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services import auth
from hotel.services import n1_core
from hotel.controllers.utils import vnd


class AdminControllerMixin:
    def add_user(self, values):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            auth.create_staff(db, actor, values['username'], values['name'],
                              values['email'], values['phone'], values['position'], values['role'])

    def reissue_staff_password(self, row_id):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            auth.reissue_staff_password(db, actor, self._must(db, User, row_id))

    def assign_staff_email(self, row_id, email):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            auth.assign_staff_email(db, actor, self._must(db, User, row_id), email)

    def archive_user(self, row_id):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            auth.archive_user(db, actor, self._must(db, User, row_id))

    def delete_staff_permanently(self, row_id):
        """Permanently remove only staff accounts; never mutate guest accounts."""
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            auth.delete_staff_permanently(db, actor, self._must(db, User, row_id))

    def reset_user_password(self, row_id, new_password):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            auth.admin_reset_password(db, actor, self._must(db, User, row_id), new_password)

    def get_settings(self):
        with self._session() as db:
            self._require_staff(db, admin=True)
            return n1_core.get_settings(db)

    def save_settings(self, values):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            n1_core.update_settings(db, actor, values)

    def save_employee(self, row_id, values):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            n1_core.save_employee(db, actor, self._must(db, User, row_id),
                                  values['phone'], values['position'])

    def toggle_user(self, row_id):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            catalog.toggle_user(db, actor, self._must(db, User, row_id))
