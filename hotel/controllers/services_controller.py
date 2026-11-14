from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd
from hotel.models.customer_services import ServiceDetails
from hotel.repositories.services import ServiceRepository
from hotel.services import service_orders


class ServicesControllerMixin:
    def save_service(self, values, row_id=None):
        with self._session(read_committed=True) as db:
            actor = self._require_staff(db, admin=True)
            service = None
            if row_id:
                service = db.scalar(select(HotelService).where(HotelService.id == int(row_id)).with_for_update())
                if service is None:
                    raise ValueError('Dịch vụ không tồn tại.')
            details = {key: values[key] for key in service_orders.details_values(None) if key in values}
            return catalog.save_service(db, actor, service,
                values['name'], values['price'], values.get('active', True), **details)

    def add_usage(self, booking_id, service_id, quantity):
        with self._session() as db:
            actor = self._require_staff(db)
            business.add_service_usage(db, self._must(db, Booking, booking_id),
                self._must(db, HotelService, service_id), catalog.positive_int(quantity, 1, 1000), actor)

    def service_catalog(self, public=False):
        with self._session() as db:
            if not public:
                self._require_staff(db)
            details = {row.service_id: row for row in db.scalars(select(ServiceDetails)).all()}
            return [dict(id=row.id, name=row.name, price=str(row.price), active=row.active,
                         schedule_label='Có' if details.get(row.id) and details[row.id].requires_schedule else 'Không',
                         **service_orders.details_values(details.get(row.id)))
                    for row in HotelRepository(db).services() if row.active or not public]

    def service_bookings(self):
        with self._session() as db:
            user = self._require_user(db)
            if user.role != 'customer':
                self._require_staff(db)
            query = select(Booking).join(Customer).where(Booking.status == 'checked_in')
            if user.role == 'customer':
                query = query.where(Customer.user_id == user.id)
            return [{'id': row.id, 'code': row.code, 'room': row.room.number,
                     'customer': row.customer.full_name} for row in db.scalars(query).all()
                    if row.invoice is None]

    def request_service(self, booking_id, service_id, quantity, *, scheduled_at='', notes='', request_token=None):
        with self._session(read_committed=True) as db:
            user = self._require_user(db)
            return service_orders.request_service(db, booking_id, service_id, quantity, user.id,
                scheduled_at=scheduled_at, notes=notes, request_token=request_token)

    def service_orders(self, booking_id=None):
        with self._session() as db:
            user = self._require_user(db)
            if user.role != 'customer':
                self._require_staff(db)
            return [{'id': row.id, 'booking_id': row.booking_id, 'code': code, 'customer': name,
                     'service': row.service_name, 'quantity': row.quantity, 'price': str(row.unit_price),
                     'amount': vnd(row.unit_price * row.quantity), 'status': row.status,
                     'scheduled_at': str(row.scheduled_at or ''), 'notes': row.notes}
                    for row, code, name in ServiceRepository(db).orders(user, booking_id)]

    def set_service_order_status(self, order_id, status):
        with self._session(read_committed=True) as db:
            user = self._require_user(db)
            return service_orders.change_status(db, order_id, status, user.id)
