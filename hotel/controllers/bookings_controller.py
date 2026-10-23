from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd


class BookingsControllerMixin:
    def book(self, values):
        start, end = date.fromisoformat(values['checkin']), date.fromisoformat(values['checkout'])
        with self._session() as db:
            actor = self._require_staff(db) if self.user else None
            booking = business.create_booking(db, name=values['name'], phone=values['phone'],
                email=values.get('email', ''), room_id=int(values['room_id']),
                checkin=start, checkout=end, guests=catalog.positive_int(values['guests'], 1, 30),
                notes=values.get('notes', ''), status='confirmed' if actor else 'pending', actor_id=actor)
            return booking.code

    def lookup(self, code, phone):
        with self._session() as db:
            booking = db.scalar(select(Booking).where(Booking.code == str(code).strip().upper()))
            if not booking or booking.customer.phone != str(phone).strip():
                raise ValueError('Không tìm thấy đơn đúng mã và số điện thoại.')
            return {'code': booking.code, 'room': booking.room.number,
                    'checkin': str(booking.checkin_date), 'checkout': str(booking.checkout_date),
                    'status': booking.status, 'customer': booking.customer.full_name}

    def set_booking_status(self, booking_id, status):
        with self._session() as db:
            actor = self._require_staff(db)
            business.change_booking_status(db, self._must(db, Booking, booking_id), status, actor)

    def calendar(self, first_day, days=7):
        start = date.fromisoformat(first_day)
        days = catalog.positive_int(days, 1, 31)
        end = start + timedelta(days=days)
        with self._session() as db:
            self._require_staff(db)
            rooms = HotelRepository(db).rooms()
            bookings = db.scalars(select(Booking).where(
                Booking.status.in_(('pending', 'confirmed', 'checked_in')),
                Booking.checkin_date < end, Booking.checkout_date > start)).all()
            headers = [(start + timedelta(days=i)).strftime('%d/%m') for i in range(days)]
            result = []
            for room in rooms:
                cells = []
                for offset in range(days):
                    day = start + timedelta(days=offset)
                    active = next((b for b in bookings if b.room_id == room.id and
                                   b.checkin_date <= day < b.checkout_date), None)
                    cells.append(active.code if active else ('—' if not room.active else 'Trống'))
                result.append({'room': room.number, 'cells': cells})
            return headers, result
