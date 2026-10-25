"""N1 authentication tests use isolated SQLite, never the configured MySQL server."""
from __future__ import annotations

import hashlib
import os
import re
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
from hotel.models.entities import (AuditLog, Booking, Customer, EmailOtp, Employee,
                                   Invoice, Payment, Role, Room, RoomType,
                                   SystemSetting, User, UserRole)
from hotel.services.security import PASSWORD_ITERATIONS, hash_password, verify_password
from hotel.services.n1_core import bootstrap_n1
from hotel.services.email_schema import migrate_email_columns
from hotel.models.common import utc_now
from hotel.services.mailer import send_email
from hotel.services.phone import normalize_phone


@pytest.fixture
def outbox(monkeypatch):
    messages = []
    monkeypatch.setenv('EMAIL_OTP_SECRET', 'testing-only-hmac-secret-not-for-production')
    monkeypatch.setattr('hotel.services.mailer.send_email',
                        lambda recipient, subject, body: messages.append((recipient, subject, body)))
    return messages


def otp_from(messages):
    return re.search(r'Mã OTP GrandStay của bạn: (\d{6})', messages[-1][2]).group(1)


@pytest.fixture
def accounts():
    engine = create_engine('sqlite:///:memory:',
                           connect_args={'check_same_thread': False}, poolclass=StaticPool)
    with engine.connect() as connection:
        connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    # Match hotel.models.database.SessionLocal (production: autoflush=False).
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with factory() as db:
        db.add(User(username='admin', full_name='Administrator',
                    password_hash=hash_password('AdminPassword123'), role='admin'))
        db.add(User(username='frontdesk', full_name='Lễ tân',
                    password_hash=hash_password('Reception123'), role='receptionist'))
        db.commit()
    yield DesktopController(factory), factory
    engine.dispose()


def test_salted_password_hash_not_plaintext_and_legacy_compatible():
    password = 'Password123!'
    first, second = hash_password(password), hash_password(password)
    assert first != second
    assert password not in first
    assert first.startswith(f'pbkdf2_sha256${PASSWORD_ITERATIONS}$')
    assert verify_password(password, first)
    assert not verify_password('wrong', first)
    salt = bytes.fromhex('01' * 16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)
    legacy = f'pbkdf2_sha256$310000${salt.hex()}${digest.hex()}'
    assert verify_password(password, legacy)


def test_register_customer_login_change_password_and_audit(accounts, outbox):
    c, factory = accounts
    c.request_registration_otp('sang@example.com')
    assert outbox[-1][0] == 'sang@example.com'
    c.register_customer('sang_01', 'Sáng', 'sang@example.com',
                        'CustomerPass123', 'CustomerPass123', otp_from(outbox), '0912345678')
    with factory() as db:
        customer = db.scalar(select(User).where(User.username == 'sang_01'))
        assert customer.role == 'customer'
        assert customer.password_hash != 'CustomerPass123'
        assert customer.email_verified_at is not None
    assert c.login('sang_01', 'CustomerPass123')['role'] == 'customer'
    assert c.login('sang@example.com', 'CustomerPass123')['role'] == 'customer'
    assert c.get_current_user()['name'] == 'Sáng'
    with pytest.raises(PermissionError):
        c.table('users')
    with pytest.raises(ValueError, match='hiện tại'):
        c.change_password('wrong', 'NewPassword123', 'NewPassword123')
    c.change_password('CustomerPass123', 'NewPassword123', 'NewPassword123')
    assert c.get_current_user()['name'] == 'Sáng'
    c.logout()
    with pytest.raises(ValueError):
        c.login('sang_01', 'CustomerPass123')
    assert c.login('sang_01', 'NewPassword123')['role'] == 'customer'
    with factory() as db:
        actions = set(db.scalars(select(AuditLog.action)).all())
        assert {'user.register', 'auth.login', 'auth.password_change'} <= actions


def test_duplicate_registration_or_bad_confirmation(accounts, outbox):
    c, factory = accounts
    c.request_registration_otp('first@example.com')
    otp = otp_from(outbox)
    with pytest.raises(ValueError, match='xác nhận'):
        c.register_customer('first_user', 'Khách', 'first@example.com',
                            'CustomerPass123', 'mismatch', otp, '0912345679')
    c.register_customer('first_user', 'Khách', 'first@example.com',
                        'CustomerPass123', 'CustomerPass123', otp, '0912345679')
    with pytest.raises(ValueError, match='tồn tại'):
        c.register_customer('first_user', 'Khách 2', 'first@example.com',
                            'CustomerPass123', 'CustomerPass123', otp, '0912345679')


def test_otp_is_single_use_limited_and_expires(accounts, outbox):
    c, factory = accounts
    c.request_registration_otp('otp@example.com')
    real_code = otp_from(outbox)
    with pytest.raises(ValueError, match='60 giây'):
        c.request_registration_otp('otp@example.com')
    for _ in range(5):
        with pytest.raises(ValueError, match='OTP không đúng'):
            c.register_customer('otp_user', 'Khách', 'otp@example.com',
                                'NewPassword123', 'NewPassword123',
                                '000000' if real_code != '000000' else '111111',
                                '0912345680')
    with pytest.raises(ValueError, match='khóa'):
        c.register_customer('otp_user', 'Khách', 'otp@example.com',
                            'NewPassword123', 'NewPassword123', real_code, '0912345680')

    c.request_registration_otp('expires@example.com')
    with factory() as db:
        otp = db.scalar(select(EmailOtp).where(EmailOtp.email == 'expires@example.com'))
        otp.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    with pytest.raises(ValueError, match='hết hạn'):
        c.register_customer('expired', 'Khách', 'expires@example.com',
                            'NewPassword123', 'NewPassword123', otp_from(outbox), '0912345681')


def test_forgot_password_email_otp_and_safe_missing_account(accounts, outbox):
    c, factory = accounts
    c.request_registration_otp('customer@example.com')
    c.register_customer('customer01', 'Khách Hàng', 'customer@example.com',
                        'OriginalPass123', 'OriginalPass123', otp_from(outbox), '0912345682')
    count = len(outbox)
    response = c.request_password_reset('unknown@example.com')
    assert 'Nếu email' in response
    assert len(outbox) == count  # No account enumeration in displayed message.
    assert c.request_password_reset('customer@example.com') == response
    code = otp_from(outbox)
    c.reset_password_with_otp('customer@example.com', code,
                              'ChangedPass123', 'ChangedPass123')
    with pytest.raises(ValueError):
        c.reset_password_with_otp('customer@example.com', code,
                                  'AnotherPassword123', 'AnotherPassword123')
    with pytest.raises(ValueError):
        c.login('customer@example.com', 'OriginalPass123')
    assert c.login('customer@example.com', 'ChangedPass123')['role'] == 'customer'


def test_password_reset_invalidates_another_open_session(accounts, outbox):
    customer_controller, factory = accounts
    customer_controller.request_registration_otp('session@example.com')
    customer_controller.register_customer('session_user', 'Khách', 'session@example.com',
                                         'OriginalPass123', 'OriginalPass123', otp_from(outbox),
                                         '0912345683')
    customer_controller.login('session_user', 'OriginalPass123')
    another_controller = DesktopController(factory)
    another_controller.login('admin', 'AdminPassword123')
    with factory() as db:
        customer_id = db.scalar(select(User.id).where(User.username == 'session_user'))
    another_controller.reset_user_password(customer_id, 'ChangedPass123')
    with pytest.raises(PermissionError, match='quyền'):
        customer_controller.get_current_user()


def test_staff_can_link_email_only_with_password_and_otp(accounts, outbox):
    c, factory = accounts
    c.login('frontdesk', 'Reception123')
    with pytest.raises(ValueError):
        c.request_link_email('badpassword', 'staff@example.com')
    c.request_link_email('Reception123', 'staff@example.com')
    code = otp_from(outbox)
    c.confirm_link_email('staff@example.com', code)
    assert c.login('staff@example.com', 'Reception123')['role'] == 'receptionist'


def test_email_login_requires_ownership_verification(accounts):
    c, factory = accounts
    with factory() as db:
        user = db.scalar(select(User).where(User.username == 'frontdesk'))
        user.email = 'unverified@example.com'
        db.commit()
    with pytest.raises(ValueError):
        c.login('unverified@example.com', 'Reception123')
    assert c.login('frontdesk', 'Reception123')['role'] == 'receptionist'


def test_smtp_uses_starttls_and_app_credentials_without_network(monkeypatch):
    calls = []
    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(('connect', host, port, timeout))
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def ehlo(self):
            calls.append(('ehlo',))
        def starttls(self, context):
            calls.append(('starttls',))
        def login(self, username, password):
            calls.append(('login', username, password))
        def send_message(self, message):
            calls.append(('send', str(message['To'])))
    monkeypatch.setenv('EMAIL_SMTP_HOST', 'smtp.example.com')
    monkeypatch.setenv('EMAIL_SMTP_PORT', '587')
    monkeypatch.setenv('EMAIL_SMTP_SECURITY', 'starttls')
    monkeypatch.setenv('EMAIL_SMTP_USER', 'sender@example.com')
    monkeypatch.setenv('EMAIL_SMTP_PASSWORD', 'app-secret')
    monkeypatch.setenv('EMAIL_FROM', 'sender@example.com')
    monkeypatch.setattr('hotel.services.mailer.smtplib.SMTP', FakeSMTP)
    send_email('target@example.com', 'Email xác minh', 'Mã xác minh dùng thử')
    assert ('starttls',) in calls
    assert ('send', 'target@example.com') in calls


def test_admin_can_reset_other_accounts_and_locked_user_cannot_login(accounts):
    c, factory = accounts
    c.login('admin', 'AdminPassword123')
    c.reset_user_password(2, 'NewReception123')
    with pytest.raises(ValueError, match='chính mình'):
        c.reset_user_password(1, 'AnotherAdmin123')
    c.toggle_user(2)
    c.logout()
    with pytest.raises(ValueError, match='khóa'):
        c.login('frontdesk', 'NewReception123')
    c.login('admin', 'AdminPassword123')
    c.toggle_user(2)
    c.logout()
    assert c.login('frontdesk', 'NewReception123')['role'] == 'receptionist'


def test_existing_pbkdf2_hash_is_upgraded_after_login(accounts):
    c, factory = accounts
    salt = bytes.fromhex('ab' * 16)
    password = 'LegacyPassword123'
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)
    with factory() as db:
        user = db.scalar(select(User).where(User.username == 'admin'))
        user.password_hash = f'pbkdf2_sha256$310000${salt.hex()}${digest.hex()}'
        db.commit()
    c.login('admin', password)
    with factory() as db:
        user = db.scalar(select(User).where(User.username == 'admin'))
        assert user.password_hash.startswith(f'pbkdf2_sha256${PASSWORD_ITERATIONS}$')
        assert verify_password(password, user.password_hash)


def test_n1_six_tables_reference_data_and_legacy_accounts(accounts):
    c, factory = accounts
    assert {'users', 'roles', 'user_roles', 'employees', 'audit_logs',
            'system_settings'} <= set(Base.metadata.tables)
    with factory() as db:
        bootstrap_n1(db)
        bootstrap_n1(db)  # idempotent when installing over an existing database
        assert len(db.scalars(select(Role)).all()) == 3
        assert len(db.scalars(select(UserRole)).all()) == 2
        assert len(db.scalars(select(Employee)).all()) == 2
        assert db.get(SystemSetting, 'hotel_name') is not None


def test_admin_hotel_settings_employee_and_role_permissions(accounts):
    c, factory = accounts
    c.login('frontdesk', 'Reception123')
    with pytest.raises(PermissionError):
        c.get_settings()
    with pytest.raises(PermissionError):
        c.save_employee(2, {'phone': '0912345678', 'position': 'Lễ tân chính'})
    c.login('admin', 'AdminPassword123')
    c.save_settings({'hotel_name': 'GrandStay Sáng', 'hotel_phone': '02412345678',
                     'checkin_time': '15:00', 'checkout_time': '11:00'})
    assert c.get_settings()['hotel_name'] == 'GrandStay Sáng'
    with pytest.raises(ValueError):
        c.save_settings({'checkin_time': '99:99'})
    c.save_employee(2, {'phone': '0912345678', 'position': 'Lễ tân chính'})
    row = next(x for x in c.table('users') if x['username'] == 'frontdesk')
    assert row['phone'] == '+84912345678' and row['position'] == 'Lễ tân chính'
    with factory() as db:
        actions = set(db.scalars(select(AuditLog.action)).all())
        assert {'system_settings.update', 'employee.update'} <= actions


def test_additive_email_migration_on_existing_sqlite_users_table():
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as db:
        db.exec_driver_sql('CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(60))')
        db.exec_driver_sql("INSERT INTO users (id, username) VALUES (1, 'existing')")
        db.exec_driver_sql('CREATE TABLE customers (id INTEGER PRIMARY KEY, full_name VARCHAR(160), phone VARCHAR(25))')
        db.exec_driver_sql("INSERT INTO customers (id, full_name, phone) VALUES (25, 'Khách cũ', '0912345678')")
    migrate_email_columns(engine)
    migrate_email_columns(engine)
    with engine.connect() as db:
        columns = {row[1] for row in db.exec_driver_sql('PRAGMA table_info(users)')}
        assert {'email', 'email_verified_at', 'phone', 'must_change_password',
                'temporary_password_expires_at', 'archived_at',
                'failed_login_attempts', 'login_blocked_until'} <= columns

        assert db.exec_driver_sql('SELECT username FROM users WHERE id=1').scalar() == 'existing'
        guest_columns = {row[1] for row in db.exec_driver_sql('PRAGMA table_info(customers)')}
        assert 'user_id' in guest_columns
        assert db.exec_driver_sql('SELECT phone FROM customers WHERE id=25').scalar() == '0912345678'
    engine.dispose()


def test_phone_normalization_customer_profile_and_duplicates(accounts, outbox):
    c, factory = accounts
    assert normalize_phone('0912 345 678') == '+84912345678'
    c.request_registration_otp('phone-one@example.com')
    code = otp_from(outbox)
    c.register_customer('phone_one', 'Khách Một', 'phone-one@example.com',
                        'CustomerPass123', 'CustomerPass123', code, '0912345678')
    with factory() as db:
        customer = db.scalar(select(User).where(User.username == 'phone_one'))
        assert customer.phone == '+84912345678'
        from hotel.models.entities import Customer
        assert db.scalar(select(Customer).where(Customer.user_id == customer.id)).phone == customer.phone
    c.request_registration_otp('phone-two@example.com')
    with pytest.raises(ValueError, match='Số điện thoại'):
        c.register_customer('phone_two', 'Khách Hai', 'phone-two@example.com',
                            'CustomerPass123', 'CustomerPass123', otp_from(outbox),
                            '+84912345678')


def test_staff_method_b_random_email_first_change_and_expiry(accounts, outbox):
    c, factory = accounts
    c.login('admin', 'AdminPassword123')
    c.add_user({'username': 'letan2', 'name': 'Nguyễn Lan',
                'email': 'letan2@example.com', 'phone': '0912333444',
                'position': 'Lễ tân', 'role': 'receptionist'})
    assert outbox[-1][0] == 'letan2@example.com'
    password = re.search(r'Mật khẩu tạm: (\S+)', outbox[-1][2]).group(1)
    with factory() as db:
        staff = db.scalar(select(User).where(User.username == 'letan2'))
        staff_id = staff.id
        employee = db.scalar(select(Employee).where(Employee.user_id == staff_id))
        assert employee is not None
        assert employee.position == 'Lễ tân'
        assert employee.phone == staff.phone
        assert staff.must_change_password and staff.temporary_password_expires_at
        assert password not in staff.password_hash
        assert staff.email_verified_at is None
    c.logout()
    assert c.login('letan2', password)['requires_password_change'] is True
    with pytest.raises(PermissionError, match='đổi mật khẩu'):
        c.table('bookings')
    c.change_password(password, 'NewStaffPassword123', 'NewStaffPassword123')
    assert c.get_current_user()['requires_password_change'] is False
    c.logout()
    assert c.login('letan2@example.com', 'NewStaffPassword123')['role'] == 'receptionist'
    with factory() as db:
        assert db.get(User, staff_id).email_verified_at is not None

    c.login('admin', 'AdminPassword123')
    c.reissue_staff_password(staff_id)
    new_password = re.search(r'Mật khẩu tạm mới: (\S+)', outbox[-1][2]).group(1)
    assert new_password != password
    with factory() as db:
        staff = db.get(User, staff_id)
        staff.temporary_password_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    c.logout()
    with pytest.raises(ValueError, match='hết hạn'):
        c.login('letan2', new_password)
    c.login('admin', 'AdminPassword123')
    c.archive_user(staff_id)
    with factory() as db:
        assert db.get(User, staff_id).archived_at is not None
    with pytest.raises(ValueError, match='ngừng sử dụng'):
        c.toggle_user(staff_id)


def test_hard_delete_archived_employee_removes_mysql_rows_and_keeps_audit(accounts, outbox):
    c, factory = accounts
    c.login('admin', 'AdminPassword123')
    c.add_user({'username': 'delete_me', 'name': 'Nhân viên Xóa',
                'email': 'delete-me@example.com', 'phone': '0912777888',
                'position': 'Lễ tân', 'role': 'receptionist'})
    with factory() as db:
        staff = db.scalar(select(User).where(User.username == 'delete_me'))
        staff_id = staff.id
        assert db.scalar(select(Employee).where(Employee.user_id == staff_id)) is not None
        assert db.scalar(select(UserRole).where(UserRole.user_id == staff_id)) is not None
    c.archive_user(staff_id)
    c.delete_staff_permanently(staff_id)
    with factory() as db:
        assert db.get(User, staff_id) is None
        assert db.scalar(select(Employee).where(Employee.user_id == staff_id)) is None
        assert db.scalar(select(UserRole).where(UserRole.user_id == staff_id)) is None
        assert db.scalar(select(AuditLog).where(AuditLog.action == 'user.hard_delete')) is not None
    assert 'delete_me' not in [row['username'] for row in c.table('users')]
    with pytest.raises(ValueError, match='Sai tài khoản'):
        c.login('delete_me', 'any')


def test_permanent_delete_cannot_remove_self_or_customer_login(accounts, outbox):
    c, factory = accounts
    c.login('admin', 'AdminPassword123')
    with pytest.raises(ValueError, match='đang đăng nhập'):
        c.delete_staff_permanently(1)
    c.request_registration_otp('readonly-customer@example.com')
    c.register_customer('readonly_customer', 'Khách Chỉ Xem',
                        'readonly-customer@example.com', 'SecureCustomer123',
                        'SecureCustomer123', otp_from(outbox), '0912555777')
    with factory() as db:
        customer = db.scalar(select(User).where(User.username == 'readonly_customer'))
        customer_id = customer.id
    with pytest.raises(PermissionError, match='khách hàng'):
        c.delete_staff_permanently(customer_id)
    with factory() as db:
        assert db.get(User, customer_id) is not None


def test_permanent_deletion_blocks_staff_with_payment_attribution(accounts, outbox):
    c, factory = accounts
    c.login('admin', 'AdminPassword123')
    c.add_user({'username': 'paid_staff', 'name': 'Lễ tân thanh toán',
                'email': 'paid-staff@example.com', 'phone': '0912444555',
                'position': 'Lễ tân', 'role': 'receptionist'})
    with factory() as db:
        staff = db.scalar(select(User).where(User.username == 'paid_staff'))
        staff_id = staff.id
        # Use a fully linked payment. FK constraints are ON, as in MySQL.
        room_type = RoomType(name='Test phòng', capacity=2,
                             nightly_price=Decimal('100000'))
        db.add(room_type)
        db.flush()
        room = Room(number='T-01', floor=1, room_type_id=room_type.id)
        customer = Customer(full_name='Khách thanh toán', phone='0998888777', email='')
        db.add_all([room, customer])
        db.flush()
        booking = Booking(code='BK-STRICT-1', customer_id=customer.id, room_id=room.id,
                          checkin_date=date.today(),
                          checkout_date=date.today() + timedelta(days=1),
                          nightly_price=Decimal('100000'), guests=1,
                          status='checked_out')
        db.add(booking)
        db.flush()
        invoice = Invoice(booking_id=booking.id, room_amount=Decimal('100000'),
                          services_amount=Decimal('0'), discount_amount=Decimal('0'),
                          total_amount=Decimal('100000'))
        db.add(invoice)
        db.flush()
        db.add(Payment(invoice_id=invoice.id, amount=Decimal('100000'), method='cash',
                       reference='TEST', recorded_by=staff_id))
        db.commit()
    with pytest.raises(ValueError, match='thanh toán'):
        c.delete_staff_permanently(staff_id)
    with factory() as db:
        assert db.get(User, staff_id) is not None


def test_initial_admin_cli_requires_verified_email_otp(accounts, outbox, monkeypatch):
    from scripts import create_admin

    _controller, factory = accounts
    monkeypatch.setattr(create_admin, 'engine', factory.kw['bind'])
    monkeypatch.setattr(create_admin, 'SessionLocal', factory)
    answers = iter(['bootstrap_admin', 'Quản trị có email', 'bootstrap@example.com'])
    monkeypatch.setattr('builtins.input', lambda prompt='':
                        otp_from(outbox) if 'OTP' in prompt else next(answers))
    monkeypatch.setattr(create_admin.getpass, 'getpass', lambda _prompt: 'StrongAdminPassword123')

    create_admin.main()

    with factory() as db:
        account = db.scalar(select(User).where(User.username == 'bootstrap_admin'))
        assert account is not None
        assert account.email == 'bootstrap@example.com'
        assert account.email_verified_at is not None
        assert account.role == 'admin'


def test_failed_smtp_creation_rolls_back_staff(accounts, monkeypatch):
    c, factory = accounts
    c.login('admin', 'AdminPassword123')
    def broken(*_args):
        raise RuntimeError('SMTP không kết nối')
    monkeypatch.setattr('hotel.services.mailer.send_email', broken)
    with pytest.raises(RuntimeError, match='SMTP'):
        c.add_user({'username': 'no_email_staff', 'name': 'Nguyễn Minh',
                    'email': 'failed@example.com', 'phone': '0912222333',
                    'position': 'Lễ tân', 'role': 'receptionist'})
    with factory() as db:
        assert db.scalar(select(User).where(User.username == 'no_email_staff')) is None


def test_legacy_employee_email_onboarding_uses_new_temporary_password(accounts, outbox):
    c, factory = accounts
    c.login('admin', 'AdminPassword123')
    c.assign_staff_email(2, 'oldfrontdesk@example.com')
    assert outbox[-1][0] == 'oldfrontdesk@example.com'
    temporary = re.search(r'Mật khẩu tạm mới: (\S+)', outbox[-1][2]).group(1)
    c.logout()
    with pytest.raises(ValueError):
        c.login('frontdesk', 'Reception123')
    assert c.login('frontdesk', temporary)['requires_password_change']
    c.change_password(temporary, 'PersonalStaffPassword123', 'PersonalStaffPassword123')
    c.logout()
    assert c.login('oldfrontdesk@example.com', 'PersonalStaffPassword123')['role'] == 'receptionist'


def test_archiving_last_admin_forbidden(accounts):
    c, factory = accounts
    c.login('admin', 'AdminPassword123')
    with pytest.raises(ValueError, match='đang sử dụng'):
        c.archive_user(1)


def test_five_bad_passwords_temporarily_block_login(accounts):
    c, factory = accounts
    for _ in range(5):
        with pytest.raises(ValueError, match='Sai tài khoản'):
            c.login('frontdesk', 'bad-password')
    with pytest.raises(ValueError, match='15 phút'):
        c.login('frontdesk', 'Reception123')
    with factory() as db:
        frontdesk = db.scalar(select(User).where(User.username == 'frontdesk'))
        frontdesk.login_blocked_until = utc_now() - timedelta(seconds=1)
        db.commit()
    assert c.login('frontdesk', 'Reception123')['role'] == 'receptionist'
