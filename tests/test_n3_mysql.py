"""Opt-in MySQL concurrency regression checks in a disposable database.

Set GRANDSTAY_N3_MYSQL_TEST_URL to a MySQL URL with CREATE DATABASE permission.
The configured application database is never used for test records.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import os
import re
from threading import Barrier
from uuid import uuid4

os.environ['GRANDSTAY_TEST_MODE'] = '1'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from hotel.controllers.desktop_controller import DesktopController
from hotel.models.database import Base
from hotel.models.entities import (Booking, Customer, HotelService, Promotion, Room, RoomType,
                                   ServiceUsage, User)
from hotel.services.security import hash_password


@pytest.fixture
def mysql_factory():
    value = os.getenv('GRANDSTAY_N3_MYSQL_TEST_URL')
    if not value:
        pytest.skip('Set GRANDSTAY_N3_MYSQL_TEST_URL to enable isolated MySQL checks.')
    url = make_url(value)
    assert url.get_backend_name() == 'mysql'
    schema = 'grandstay_n3_check_' + uuid4().hex[:12]
    admin = create_engine(url.set(database=None), isolation_level='AUTOCOMMIT')
    engine, created = None, False
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE `{schema}` CHARACTER SET utf8mb4')
            created = True
        engine = create_engine(url.set(database=schema), pool_size=6)
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        day = date.today() + timedelta(days=1)
        with factory() as db:
            db.add(User(username='test_admin', full_name='Test admin', role='admin',
                        password_hash=hash_password('TemporaryTestPassword123')))
            db.add(RoomType(name='Test type', capacity=3, nightly_price=100000))
            db.flush()
            db.add(HotelService(name='Test spa', price=50000))
            for index in (1, 2):
                db.add(Customer(full_name=f'Test guest {index}', phone=f'090000000{index}'))
                db.add(Room(number=str(index), floor=1, room_type_id=1))
            db.flush()
            for index in (1, 2):
                db.add(Booking(code=f'TEST-{index}', customer_id=index, room_id=index,
                    checkin_date=day, checkout_date=day + timedelta(days=2),
                    nightly_price=100000, guests=2, status='checked_in'))
            db.commit()
        yield factory, day
    finally:
        if engine:
            engine.dispose()
        if created:
            assert re.fullmatch(r'grandstay_n3_check_[0-9a-f]{12}', schema) and schema != url.database
            with admin.connect() as connection:
                connection.exec_driver_sql(f'DROP DATABASE `{schema}`')
        admin.dispose()


def controller(factory):
    result = DesktopController(factory)
    result.login('test_admin', 'TemporaryTestPassword123')
    return result


def run_together(factory, action):
    start = Barrier(2)

    def worker(booking_id):
        instance = controller(factory)
        start.wait(timeout=10)
        return action(instance, booking_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(worker, (1, 2)))


def test_mysql_capacity_completion_promotion_limit_and_invoice_serialization(mysql_factory):
    factory, day = mysql_factory
    c = controller(factory)
    c.save_service({'name': 'Test spa', 'price': 50000, 'requires_schedule': True,
                    'duration_minutes': 60, 'slot_capacity': 1}, 1)

    def request_slot(worker, booking_id):
        try:
            return worker.request_service(booking_id, 1, 1, scheduled_at=f'{day} 10:00')
        except ValueError as exc:
            assert 'đủ suất' in str(exc)
            return None

    results = run_together(factory, request_slot)
    assert sum(row is not None for row in results) == 1
    order_id = next(row for row in results if row is not None)
    c.set_service_order_status(order_id, 'confirmed')
    usages = run_together(factory, lambda worker, _: worker.set_service_order_status(order_id, 'completed'))
    assert usages[0] == usages[1]
    with factory() as db:
        assert db.scalar(select(func.count(ServiceUsage.id))) == 1

    c.save_promotion({'code': 'TEST10', 'name': 'Test promotion', 'discount_type': 'percent',
        'value': 10, 'starts_on': str(date.today()), 'ends_on': str(day), 'usage_limit': 1})

    def redeem(worker, booking_id):
        try:
            return worker.apply_promotion(booking_id, 'TEST10')
        except ValueError as exc:
            assert 'hết lượt' in str(exc)
            return None

    assert sum(row is not None for row in run_together(factory, redeem)) == 1
    with factory() as db:
        assert db.get(Promotion, 1).used_count == 1
    invoices = run_together(factory, lambda worker, _: worker.make_invoice(1))
    assert invoices[0] == invoices[1]
    assert c.make_invoice(2)
