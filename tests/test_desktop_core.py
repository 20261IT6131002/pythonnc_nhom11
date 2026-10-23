"""Pure controller/service tests on throwaway SQLite; NEVER touch live MySQL."""
import os
from datetime import date, timedelta
from decimal import Decimal

os.environ['GRANDSTAY_TEST_MODE'] = '1'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hotel.controllers.desktop_controller import DesktopController
from hotel.models.database import Base
from hotel.models.entities import Booking, HotelService, Room, RoomType, User
from hotel.services.security import hash_password


@pytest.fixture
def hotel():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False},
                           poolclass=StaticPool)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with factory() as db:
        room_type = RoomType(name='Deluxe', capacity=3, nightly_price=Decimal('600000'))
        db.add(room_type)
        db.flush()
        db.add(Room(number='201', floor=2, room_type_id=room_type.id))
        db.add(HotelService(name='Giặt là', price=Decimal('50000')))
        db.add(User(username='admin', full_name='Admin Test',
                    password_hash=hash_password('StrongAdmin123'), role='admin'))
        db.add(User(username='reception', full_name='Staff Test',
                    password_hash=hash_password('StrongStaff123'), role='receptionist'))
        db.commit()
    c = DesktopController(factory)
    yield c, factory
    engine.dispose()


def request(room_id=1, name='Nguyễn Văn A', phone='0912345678', offset=2, nights=2):
    start = date.today() + timedelta(days=offset)
    return {'room_id': room_id, 'name': name, 'phone': phone, 'email': 'a@example.com',
            'checkin': str(start), 'checkout': str(start + timedelta(days=nights)),
            'guests': '2', 'notes': 'Đặt phòng thử'}


def test_guest_search_reserve_lookup_and_overlap(hotel):
    c, factory = hotel
    value = request()
    assert c.public_types()[0]['name'] == 'Deluxe'
    assert c.public_services()[0]['name'] == 'Giặt là'
    assert len(c.available(value['checkin'], value['checkout'], 2, room_type_id=1)) == 1
    assert len(c.available(value['checkin'], value['checkout'], 2)) == 1
    code = c.book(value)
    assert code.startswith('BK-')
    assert c.lookup(code, value['phone'])['status'] == 'pending'
    with pytest.raises(ValueError):
        c.lookup(code, '00000000')
    assert c.available(value['checkin'], value['checkout'], 2) == []
    with pytest.raises(ValueError, match='trùng'):
        c.book(value)
    with factory() as db:
        assert db.scalar(select(Booking)).nightly_price == Decimal('600000')


def test_staff_lifecycle_payment_pdf_and_calendar(hotel, tmp_path):
    c, factory = hotel
    c.login('admin', 'StrongAdmin123')
    code = c.book(request())  # staff books as confirmed
    row_id = c.table('bookings')[0]['id']
    assert c.table('bookings')[0]['status'] == 'confirmed'
    headers, rows = c.calendar(request()['checkin'], 7)
    assert len(headers) == 7 and any(code in x['cells'] for x in rows)
    c.set_booking_status(row_id, 'checked_in')
    c.add_usage(row_id, 1, 2)
    invoice_id = c.make_invoice(row_id)
    assert c.table('invoices')[0]['total'].startswith('1,300,000')
    with pytest.raises(ValueError, match='thanh toán'):
        c.set_booking_status(row_id, 'checked_out')
    c.pay(invoice_id, '500000', 'cash')
    with pytest.raises(ValueError):
        c.pay(invoice_id, '900000', 'cash')
    c.pay(invoice_id, '800000', 'bank_transfer', 'TX123')
    c.set_booking_status(row_id, 'checked_out')
    assert c.table('bookings')[0]['status'] == 'checked_out'
    target = tmp_path / 'invoice.pdf'
    c.export_invoice(invoice_id, target)
    assert target.read_bytes().startswith(b'%PDF')


def test_permissions_and_admin_catalog(hotel):
    c, factory = hotel
    with pytest.raises(ValueError):
        c.login('admin', 'wrong')
    c.login('reception', 'StrongStaff123')
    with pytest.raises(PermissionError):
        c.save_type({'name': 'VIP', 'capacity': '4', 'price': '2000000'})
    with pytest.raises(PermissionError):
        c.table('users')
    c.login('admin', 'StrongAdmin123')
    c.save_type({'name': 'VIP', 'capacity': '4', 'price': '2000000'})
    assert len(c.table('types')) == 2
    c.save_room({'number': '301', 'type_id': 2, 'floor': '3'})
    assert len(c.table('rooms')) == 2
    c.toggle_room(2)
    assert c.table('rooms')[1]['active'] is False
    c.add_user({'username': 'staff2', 'name': 'Nguyễn Văn B',
                'password': 'StrongPass123', 'role': 'receptionist'})
    assert len(c.table('users')) == 3


def test_validate_dates_price_and_chatbot(hotel):
    c, _ = hotel
    bad = request(nights=0)
    with pytest.raises(ValueError):
        c.book(bad)
    assert 'Deluxe' in c.ask_chatbot('Giá phòng Deluxe bao nhiêu?')
    assert 'Giặt là' in c.ask_chatbot('Bạn có dịch vụ nào?')
    c.login('admin', 'StrongAdmin123')
    with pytest.raises(ValueError):
        c.save_service({'name': 'Spa', 'price': '-2000', 'active': True})
