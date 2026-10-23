from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd


class CatalogControllerMixin:
    def choices(self, kind):
        with self._session() as db:
            repo = HotelRepository(db)
            if kind == 'types':
                return [(r.id, f'{r.id} - {r.name}') for r in repo.types()]
            if kind == 'rooms':
                return [(r.id, f'{r.id} - Phòng {r.number} ({r.room_type.name})')
                        for r in repo.rooms() if r.active]
            if kind == 'services':
                return [(r.id, f'{r.id} - {r.name}') for r in repo.services() if r.active]
            if kind == 'stays':
                self._require_staff(db)
                return [(r.id, f'{r.id} - {r.code} / {r.customer.full_name}')
                        for r in repo.bookings() if r.status == 'checked_in' and r.invoice is None]
            raise ValueError('Danh mục không hỗ trợ.')

    def public_types(self):
        """Bảng giá công khai để hiển thị thẻ loại phòng tại trang chủ."""
        with self._session() as db:
            return [{'id': x.id, 'name': x.name, 'capacity': x.capacity,
                     'price': vnd(x.nightly_price), 'description': x.description}
                    for x in HotelRepository(db).types()]

    def public_services(self):
        with self._session() as db:
            return [{'name': x.name, 'price': vnd(x.price)}
                    for x in HotelRepository(db).services() if x.active]

    def table(self, kind):
        with self._session() as db:
            self._require_staff(db, admin=(kind in ('users', 'logs')))
            repo = HotelRepository(db)
            if kind == 'types':
                return [{'id': x.id, 'name': x.name, 'capacity': x.capacity,
                         'price': str(x.nightly_price), 'description': x.description} for x in repo.types()]
            if kind == 'rooms':
                return [{'id': x.id, 'number': x.number, 'type': x.room_type.name,
                         'type_id': x.room_type_id, 'floor': x.floor, 'active': x.active,
                         'price': str(x.room_type.nightly_price)} for x in repo.rooms()]
            if kind == 'customers':
                return [{'id': x.id, 'name': x.full_name, 'phone': x.phone,
                         'email': x.email, 'document_no': x.document_no} for x in repo.customers()]
            if kind == 'bookings':
                return [{'id': x.id, 'code': x.code, 'customer': x.customer.full_name,
                         'phone': x.customer.phone, 'room': x.room.number,
                         'checkin': str(x.checkin_date), 'checkout': str(x.checkout_date),
                         'guests': x.guests, 'status': x.status,
                         'estimate': vnd(x.nightly_price * (x.checkout_date - x.checkin_date).days)}
                        for x in repo.bookings()]
            if kind == 'services':
                return [{'id': x.id, 'name': x.name, 'price': str(x.price),
                         'active': x.active} for x in repo.services()]
            if kind == 'invoices':
                return [{'id': x.id, 'code': x.booking.code, 'customer': x.booking.customer.full_name,
                         'room': vnd(x.room_amount), 'services': vnd(x.services_amount),
                         'total': vnd(x.total_amount), 'paid': vnd(x.total_amount - business.invoice_due(x)),
                         'due': vnd(business.invoice_due(x))} for x in repo.invoices()]
            if kind == 'users':
                return [{'id': x.id, 'username': x.username, 'name': x.full_name,
                         'role': x.role, 'active': x.active} for x in repo.users()]
            if kind == 'logs':
                return [{'id': x.id, 'date': str(x.created_at), 'actor': x.actor_id or '-',
                         'action': x.action, 'details': x.details} for x in repo.logs()]
            raise ValueError('Loại bảng không hợp lệ.')

    def dashboard(self):
        with self._session() as db:
            self._require_staff(db)
            repo = HotelRepository(db)
            today = date.today()
            _, today_total = business.revenue_summary(db, today, today)
            return {'rooms': len([r for r in repo.rooms() if r.active]),
                    'customers': repo.count(Customer), 'bookings': repo.count(Booking),
                    'staying': repo.count_bookings_with_status('checked_in'),
                    'revenue': vnd(today_total), 'recent': [
                        (b.code, b.customer.full_name, b.room.number, b.status)
                        for b in repo.bookings()[:10]]}
