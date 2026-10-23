from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd


class RoomsControllerMixin:
    def save_type(self, values, row_id=None):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            if row_id:
                catalog.edit_type(db, actor, self._must(db, RoomType, row_id),
                                  values['capacity'], values['price'], values.get('description', ''))
            else:
                catalog.add_type(db, actor, values['name'], values['capacity'],
                                 values['price'], values.get('description', ''))

    def save_room(self, values, row_id=None):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            if row_id:
                catalog.edit_room(db, actor, self._must(db, Room, row_id),
                                  values['type_id'], values['floor'])
            else:
                catalog.add_room(db, actor, values['number'], values['type_id'], values['floor'])

    def toggle_room(self, row_id):
        with self._session() as db:
            actor = self._require_staff(db, admin=True)
            catalog.toggle_room(db, actor, self._must(db, Room, row_id))

    def available(self, checkin, checkout, guests=1, room_type_id=None):
        start, end = date.fromisoformat(checkin), date.fromisoformat(checkout)
        guests = catalog.positive_int(guests, 1, 30)
        with self._session() as db:
            return [{'id': x.id, 'number': x.number, 'type': x.room_type.name,
                     'floor': x.floor, 'description': x.room_type.description,
                     'capacity': x.room_type.capacity, 'price': vnd(x.room_type.nightly_price)}
                    for x in business.find_rooms(db, start, end, guests=guests,
                                                  room_type_id=room_type_id)]
