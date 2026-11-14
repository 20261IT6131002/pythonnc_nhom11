"""N3 regressions run on disposable SQLite with the existing Controller facade."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import sessionmaker

from test_desktop_core import hotel, request
from hotel.models.database import Base
from hotel.models.entities import (Booking, BookingGuest, BookingPromotion, Customer,
    CustomerProfile, HotelService, Invoice, InvoiceCustomerSnapshot, Promotion, ServiceOrder,
    ServiceUsage, User)
from hotel.services import business, pdf_service
from hotel.services.security import hash_password


@pytest.fixture
def n3(hotel):
    controller, factory = hotel
    with factory.kw['bind'].connect() as connection:
        connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    with factory() as db:
        for index in (1, 2):
            user = User(username=f'guest{index}', full_name=f'Guest {index}', role='customer',
                phone=f'091234560{index}', email=f'guest{index}@example.com',
                password_hash=hash_password('CustomerPass123'))
            db.add(user)
            db.flush()
            db.add(Customer(user_id=user.id, full_name=user.full_name,
                            phone=user.phone, email=user.email))
        db.commit()
    controller.login('admin', 'StrongAdmin123')
    return controller, factory


def reserve(controller, *, room_id=1, customer_id=None):
    values = request(room_id=room_id, offset=1)
    if customer_id:
        row = controller.customer_details(customer_id)
        values.update(customer_id=customer_id, phone=row['phone'])
    code = controller.book(values)
    booking_id = next(row['id'] for row in controller.table('bookings') if row['code'] == code)
    controller.set_booking_status(booking_id, 'checked_in')
    return booking_id


def promotion(**changes):
    values = {'code': 'WELCOME10', 'name': 'Welcome offer', 'discount_type': 'percent',
              'value': '10', 'minimum_amount': '100000', 'starts_on': str(date.today()),
              'ends_on': str(date.today() + timedelta(days=30)), 'usage_limit': '2', 'active': True}
    return dict(values, **changes)


def test_profile_search_spending_history_and_invoice_identity_are_preserved(n3, monkeypatch):
    c, factory = n3
    booking_id = reserve(c)
    invoice_id = c.make_invoice(booking_id)
    c.pay(invoice_id, '200000', 'cash')
    with factory() as db:
        customer_id = db.get(Booking, booking_id).customer_id
        original_name = db.get(Customer, customer_id).full_name
        # Simulate an invoice issued by an older application without N3 snapshots.
        db.delete(db.get(InvoiceCustomerSnapshot, invoice_id))
        db.commit()
    c.save_customer({'name': 'Corporate guest', 'phone': '0912345678', 'email': 'corp@example.com',
                     'category': 'corporate', 'organization': 'Example Ltd', 'preferences': 'Quiet room'}, customer_id)
    assert c.search_customers('CORPORATE')[0]['id'] == customer_id
    assert c.search_customers('corp@example.com')[0]['id'] == customer_id
    assert c.search_customers(str(customer_id))[0]['id'] == customer_id
    detail = c.customer_details(customer_id)
    assert detail['booking_count'] == detail['stay_count'] == 1
    assert detail['paid_total'].startswith('200,000')
    assert detail['category'] == 'corporate' and detail['preferences'] == 'Quiet room'
    c.save_customer({'name': 'Second edit', 'phone': '0912345678'}, customer_id)
    captured = []
    monkeypatch.setattr(pdf_service, '_build', lambda _title, _headers, rows, _footers: captured.extend(rows))
    with factory() as db:
        snapshot = db.get(InvoiceCustomerSnapshot, invoice_id)
        assert snapshot.full_name == original_name
        pdf_service.invoice_pdf(db.get(Invoice, invoice_id), snapshot)
    assert ('Khách hàng', original_name) in captured
    assert c.table('invoices')[0]['customer'] == original_name


def test_customer_updates_only_own_profile_without_granting_vip_or_changing_identity(n3):
    c, factory = n3
    c.login('guest1', 'CustomerPass123')
    c.save_own_customer_profile({'name': 'Updated guest', 'address': 'HCM', 'category': 'vip',
                                'user_id': 999, 'phone': '0988888888', 'email': 'other@example.com'})
    own = c.own_customer_profile()
    assert own['category'] == 'normal' and own['phone'] == '0912345601'
    assert own['email'] == 'guest1@example.com' and own['address'] == 'HCM'
    with pytest.raises(PermissionError):
        c.customer_details(2)
    with pytest.raises(PermissionError):
        c.search_customers('')
    with pytest.raises(ValueError):
        c.save_own_customer_profile({'name': 'Should roll back', 'birth_date': '3000-01-01'})
    assert c.own_customer_profile()['name'] == 'Updated guest'
    with factory() as db:
        assert db.get(Customer, 2).full_name == 'Guest 2'


def test_staying_list_guest_capacity_primary_guest_and_closed_booking(n3):
    c, factory = n3
    booking_id = reserve(c)
    first = c.save_booking_guest(booking_id, {'name': 'First guest', 'is_primary': True})
    second = c.save_booking_guest(booking_id, {'name': 'Second guest', 'is_primary': True})
    guests = c.booking_guests(booking_id)
    assert sum(row['is_primary'] for row in guests) == 1
    assert guests[0]['id'] == second
    with pytest.raises(ValueError, match='đủ'):
        c.save_booking_guest(booking_id, {'name': 'Extra guest'})
    with pytest.raises(ValueError, match='không thuộc'):
        c.save_booking_guest(booking_id, {'name': 'Wrong guest'}, 999)
    assert c.staying_customers()[0]['registered'] == 2
    invoice_id = c.make_invoice(booking_id)
    c.pay(invoice_id, '1200000', 'cash')
    c.set_booking_status(booking_id, 'checked_out')
    assert c.staying_customers() == []
    with pytest.raises(ValueError, match='hiệu lực'):
        c.save_booking_guest(booking_id, {'name': 'Late edit'}, first)


def test_service_order_snapshots_price_posts_once_and_preserves_legacy_usage(n3):
    c, factory = n3
    booking_id = reserve(c)
    c.add_usage(booking_id, 1, 1)
    order_id = c.request_service(booking_id, 1, 2, request_token='request-1')
    assert c.request_service(booking_id, 1, 2, request_token='request-1') == order_id
    with pytest.raises(ValueError, match='nội dung khác'):
        c.request_service(booking_id, 1, 3, request_token='request-1')
    c.save_service({'name': 'New catalog name', 'price': '90000', 'active': False}, 1)
    with pytest.raises(ValueError, match='dịch vụ'):
        c.make_invoice(booking_id)
    with pytest.raises(ValueError):
        c.set_service_order_status(order_id, 'completed')
    c.set_service_order_status(order_id, 'confirmed')
    usage_id = c.set_service_order_status(order_id, 'completed')
    assert c.set_service_order_status(order_id, 'completed') == usage_id
    invoice_id = c.make_invoice(booking_id)
    with factory() as db:
        assert db.scalar(select(func.count(ServiceUsage.id))) == 2
        order = db.get(ServiceOrder, order_id)
        assert order.service_name == 'Giặt là' and order.unit_price == Decimal('50000')
        assert db.get(Invoice, invoice_id).services_amount == Decimal('150000')
    with pytest.raises(ValueError, match='chốt'):
        c.request_service(booking_id, 1, 1)


def test_order_access_is_scoped_to_account_and_customer_cancellation_is_pending_only(n3):
    c, factory = n3
    booking_id = reserve(c, customer_id=1)
    c.login('guest1', 'CustomerPass123')
    order_id = c.request_service(booking_id, 1, 1)
    with pytest.raises(PermissionError):
        c.set_service_order_status(order_id, 'confirmed')
    c.login('guest2', 'CustomerPass123')
    assert c.service_orders() == [] and c.service_bookings() == []
    with pytest.raises(PermissionError):
        c.request_service(booking_id, 1, 1)
    with pytest.raises(PermissionError):
        c.set_service_order_status(order_id, 'cancelled')
    c.login('guest1', 'CustomerPass123')
    c.set_service_order_status(order_id, 'cancelled')
    assert c.service_orders()[0]['status'] == 'cancelled'
    c.login('admin', 'StrongAdmin123')
    invoice_id = c.make_invoice(booking_id)
    with factory() as db:
        assert db.get(Invoice, invoice_id).services_amount == 0


def test_schedule_capacity_overlaps_adjacent_appointments_and_legacy_bypass(n3):
    c, factory = n3
    first = reserve(c)
    c.save_room({'number': '202', 'type_id': 1, 'floor': 2})
    second = reserve(c, room_id=2)
    c.save_service({'name': 'Spa', 'price': '200000', 'requires_schedule': True,
                    'duration_minutes': 60, 'slot_capacity': 1}, 1)
    day = str(date.today() + timedelta(days=1))
    order = c.request_service(first, 1, 1, scheduled_at=f'{day} 10:00', request_token='spa-1')
    assert c.request_service(first, 1, 1, scheduled_at=f'{day} 10:00', request_token='spa-1') == order
    with pytest.raises(ValueError, match='nội dung khác'):
        c.request_service(first, 1, 1, scheduled_at=f'{day} 11:00', request_token='spa-1')
    with pytest.raises(ValueError, match='đủ suất'):
        c.request_service(second, 1, 1, scheduled_at=f'{day} 10:30')
    adjacent = c.request_service(second, 1, 1, scheduled_at=f'{day} 11:00')
    assert adjacent != order
    with pytest.raises(ValueError, match='lịch hẹn'):
        c.add_usage(first, 1, 1)
    with pytest.raises(ValueError, match='lịch hẹn'):
        c.request_service(first, 1, 1)
    c.set_service_order_status(order, 'cancelled')
    assert c.request_service(second, 1, 1, scheduled_at=f'{day} 10:00')


def test_service_reservation_counts_peak_capacity_instead_of_sum_of_all_overlaps(n3):
    c, _ = n3
    booking_id = reserve(c)
    c.save_service({'name': 'Spa', 'price': '100000', 'requires_schedule': True,
                    'duration_minutes': 30, 'slot_capacity': 2}, 1)
    day = str(date.today() + timedelta(days=1))
    c.request_service(booking_id, 1, 1, scheduled_at=f'{day} 10:00')
    c.request_service(booking_id, 1, 1, scheduled_at=f'{day} 10:30')
    c.save_service({'name': 'Spa', 'price': '100000', 'requires_schedule': True,
                    'duration_minutes': 60, 'slot_capacity': 2}, 1)
    assert c.request_service(booking_id, 1, 1, scheduled_at=f'{day} 10:00')
    with pytest.raises(ValueError, match='sức chứa'):
        c.save_service({'name': 'Spa', 'price': '100000', 'slot_capacity': 1}, 1)


def test_promotion_snapshot_limit_idempotence_and_invoice_integration(n3):
    c, factory = n3
    promotion_id = c.save_promotion(promotion(usage_limit='1'))
    booking_id = reserve(c)
    assert c.apply_promotion(booking_id, 'welcome10').startswith('120,000')
    assert c.apply_promotion(booking_id, 'WELCOME10').startswith('120,000')
    c.save_promotion(promotion(value='50', usage_limit='1', active=False), promotion_id)
    c.add_usage(booking_id, 1, 1)
    invoice_id = c.make_invoice(booking_id)
    assert c.make_invoice(booking_id) == invoice_id
    with factory() as db:
        assert db.get(Promotion, promotion_id).used_count == 1
        invoice = db.get(Invoice, invoice_id)
        assert invoice.discount_amount == Decimal('120000')
        assert invoice.total_amount == Decimal('1130000')
    assert c.promotions(public=True) == []
    c.save_promotion(promotion(usage_limit='1'), promotion_id)
    c.save_room({'number': '202', 'type_id': 1, 'floor': 2})
    other = reserve(c, room_id=2)
    with pytest.raises(ValueError, match='hết lượt'):
        c.apply_promotion(other, 'WELCOME10')


def test_bad_promotion_rolls_back_new_booking_and_fixed_discount_is_capped(n3):
    c, factory = n3
    values = dict(request(), promotion_code='MISSING')
    with factory() as db:
        before = db.scalar(select(func.count(Customer.id)))
    with pytest.raises(ValueError, match='khuyến mãi'):
        c.book(values)
    with factory() as db:
        assert db.scalar(select(func.count(Customer.id))) == before
        assert db.scalar(select(func.count(Booking.id))) == 0
    c.save_promotion(promotion(discount_type='fixed', value='5000000'))
    c.book(dict(values, promotion_code='WELCOME10'))
    with factory() as db:
        assert db.scalar(select(BookingPromotion)).discount_amount == Decimal('1200000')


@pytest.mark.parametrize('changes', [
    {'value': '101'}, {'value': '-1'}, {'ends_on': '2000-01-01'},
    {'code': 'bad code'}, {'usage_limit': '0'},
])
def test_invalid_promotions_are_rejected_without_partial_writes(n3, changes):
    c, factory = n3
    with pytest.raises(ValueError):
        c.save_promotion(promotion(**changes))
    with factory() as db:
        assert db.scalar(select(func.count(Promotion.id))) == 0


def test_promotions_permissions_expiry_and_minimum_spend(n3):
    c, factory = n3
    booking_id = reserve(c, customer_id=1)
    c.save_promotion(promotion(minimum_amount='2000000'))
    c.save_promotion(promotion(code='EXPIRED', starts_on='2000-01-01', ends_on='2001-01-01'))
    c.login('reception', 'StrongStaff123')
    with pytest.raises(PermissionError):
        c.save_promotion(promotion(code='STAFF'))
    with pytest.raises(PermissionError):
        c.save_service({'name': 'Denied', 'price': '1'})
    with pytest.raises(ValueError, match='tối thiểu'):
        c.apply_promotion(booking_id, 'WELCOME10')
    with pytest.raises(ValueError, match='hết hạn'):
        c.apply_promotion(booking_id, 'EXPIRED')
    c.login('guest2', 'CustomerPass123')
    with pytest.raises(PermissionError):
        c.apply_promotion(booking_id, 'WELCOME10')
    with factory() as db:
        assert db.scalar(select(func.count(BookingPromotion.booking_id))) == 0


def test_new_references_preserve_existing_staff_deletion_and_service_history(n3):
    c, factory = n3
    booking_id = reserve(c)
    c.save_promotion(promotion())
    c.login('reception', 'StrongStaff123')
    staff_id = c.user['id']
    order_id = c.request_service(booking_id, 1, 1)
    c.set_service_order_status(order_id, 'confirmed')
    c.apply_promotion(booking_id, 'WELCOME10')
    c.login('admin', 'StrongAdmin123')
    c.delete_staff_permanently(staff_id)
    with factory() as db:
        order = db.get(ServiceOrder, order_id)
        assert order.requested_by is None and order.confirmed_by is None
        assert db.get(BookingPromotion, booking_id).applied_by is None
    c.set_service_order_status(order_id, 'completed')
    assert c.make_invoice(booking_id)


def test_existing_schema_and_records_survive_additive_table_creation():
    engine = create_engine('sqlite:///:memory:')
    additions = {'customer_profiles', 'booking_guests', 'service_details', 'service_orders',
                 'promotions', 'booking_promotions', 'invoice_customer_snapshots'}
    legacy_tables = [table for name, table in Base.metadata.tables.items() if name not in additions]
    Base.metadata.create_all(engine, tables=legacy_tables)
    original_columns = {name: [column['name'] for column in inspect(engine).get_columns(name)]
                        for name in ('customers', 'hotel_services', 'bookings', 'invoices')}
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(Customer(full_name='Historic customer', phone='0900000000'))
        db.add(HotelService(name='Historic service', price=12345))
        db.commit()
    Base.metadata.create_all(engine)
    Base.metadata.create_all(engine)
    for name, columns in original_columns.items():
        assert [column['name'] for column in inspect(engine).get_columns(name)] == columns
    with factory() as db:
        assert db.get(Customer, 1).full_name == 'Historic customer'
        assert db.get(HotelService, 1).price == 12345
    engine.dispose()
