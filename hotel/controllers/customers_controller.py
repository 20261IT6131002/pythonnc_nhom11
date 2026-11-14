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
from hotel.models.customer_services import CustomerProfile
from hotel.repositories.customers import CustomerRepository
from hotel.services import customers
from hotel.services.service_orders import locked_booking


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
        with self._session(read_committed=True) as db:
            actor = self._require_staff(db)
            customer = None
            if row_id:
                customer = db.scalar(select(Customer).where(Customer.id == int(row_id)).with_for_update())
                if customer is None:
                    raise ValueError('Hồ sơ khách không tồn tại.')
            profile = {key: values[key] for key in customers.profile_values(None) if key in values}
            return catalog.save_customer(db, actor, customer,
                                  values['name'], values['phone'], values.get('email', ''),
                                  values.get('document_no', ''), **profile)

    def search_customers(self, query=''):
        with self._session() as db:
            self._require_staff(db)
            rows = CustomerRepository(db).search(query)
            profiles = {x.customer_id: x for x in db.scalars(select(CustomerProfile)
                .where(CustomerProfile.customer_id.in_([row.id for row in rows]))).all()}
            return [dict(id=row.id, name=row.full_name, phone=row.phone, email=row.email,
                         document_no=row.document_no,
                         linked='Đã liên kết' if row.user_id else 'Khách tại quầy',
                         category_label=customers.CATEGORY_NAMES[
                             profiles[row.id].category if row.id in profiles else 'normal'],
                         **customers.profile_values(profiles.get(row.id))) for row in rows]

    def customer_details(self, customer_id):
        with self._session() as db:
            self._require_staff(db)
            customer = self._must(db, Customer, customer_id)
            return self._customer_details(db, customer)

    @staticmethod
    def _customer_details(db, customer, customer_ids=None):
        repo = CustomerRepository(db)
        customer_ids = customer_ids or [customer.id]
        bookings = repo.bookings(customer_ids)
        return {'id': customer.id, 'name': customer.full_name, 'phone': customer.phone,
                'email': customer.email, 'document_no': customer.document_no,
                **customers.profile_values(db.get(CustomerProfile, customer.id)),
                'booking_count': len(bookings),
                'stay_count': sum(row.status in ('checked_in', 'checked_out') for row in bookings),
                'paid_total': vnd(repo.paid_total(customer_ids)),
                'history': [{'id': row.id, 'code': row.code, 'room': row.room.number,
                             'checkin': str(row.checkin_date), 'checkout': str(row.checkout_date),
                             'status': row.status, 'checked_in_at': str(row.checked_in_at or ''),
                             'checked_out_at': str(row.checked_out_at or '')} for row in bookings]}

    def own_customer_profile(self):
        with self._session() as db:
            user = self._require_user(db)
            if user.role != 'customer':
                raise PermissionError('Chỉ tài khoản khách hàng được cập nhật hồ sơ cá nhân.')
            customer = db.scalar(select(Customer).where(Customer.user_id == user.id)
                                 .order_by(Customer.id).limit(1))
            if customer:
                ids = db.scalars(select(Customer.id).where(Customer.user_id == user.id)).all()
                return self._customer_details(db, customer, ids)
            return dict(id=None, name=user.full_name, phone=user.phone or '',
                        email=user.email or '', document_no='', **customers.profile_values(None),
                        booking_count=0, stay_count=0, paid_total=vnd(0), history=[])

    def save_own_customer_profile(self, values):
        with self._session(read_committed=True) as db:
            user = self._require_user(db)
            if user.role != 'customer':
                raise PermissionError('Chỉ tài khoản khách hàng được cập nhật hồ sơ cá nhân.')
            if not user.phone:
                raise ValueError('Cần cập nhật SĐT tài khoản trước khi lưu hồ sơ.')
            customer = db.scalar(select(Customer).where(Customer.user_id == user.id)
                                 .order_by(Customer.id).limit(1).with_for_update())
            name = catalog.checked_name(values['name'], 2, 120)
            if customer is None:
                customer = Customer(user_id=user.id, full_name=name,
                                    phone=user.phone, email=user.email or '')
                db.add(customer)
                db.flush()
            else:
                customers.preserve_invoice_customers(db, customer)
                customer.full_name = name
            customers.update_profile(db, customer, values, allow_category=False)
            user.full_name = name
            business.log_event(db, user.id, 'customer.profile_update', str(customer.id))
            db.commit()
            self.user['name'] = name

    def staying_customers(self):
        with self._session() as db:
            self._require_staff(db)
            repo = CustomerRepository(db)
            return [{'id': row.id, 'code': row.code, 'customer': row.customer.full_name,
                     'phone': row.customer.phone, 'room': row.room.number, 'guests': row.guests,
                     'registered': len(repo.guests(row.id)), 'checkin': str(row.checked_in_at or ''),
                     'checkout': str(row.checkout_date)} for row in repo.staying()]

    def booking_guests(self, booking_id):
        with self._session() as db:
            self._require_staff(db)
            self._must(db, Booking, booking_id)
            return [{'id': row.id, 'name': row.full_name, 'document_no': row.document_no,
                     'birth_date': str(row.birth_date or ''), 'nationality': row.nationality,
                     'is_primary': row.is_primary} for row in CustomerRepository(db).guests(int(booking_id))]

    def save_booking_guest(self, booking_id, values, guest_id=None):
        with self._session(read_committed=True) as db:
            actor = self._require_staff(db)
            booking = locked_booking(db, booking_id)
            return customers.save_booking_guest(db, booking, values, actor,
                                               int(guest_id) if guest_id is not None else None)
