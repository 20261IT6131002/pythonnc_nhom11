"""Account workflows shared by Tkinter controllers.

Passwords are never persisted or logged in plaintext. Customer identity here is
limited to the login account; N3 owns the separate customer profile workflow.
"""
from __future__ import annotations

import re
import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from hotel.models.entities import (AuditLog, Customer, CustomerLinkRequest,
                                   EmailOtp, Employee, Payment, User, UserRole)
from hotel.services.business import log_event
from hotel.services.security import hash_password, password_needs_rehash, validate_password, verify_password
from hotel.services.n1_core import attach_role_and_employee
from hotel.services import email_otp, mailer
from hotel.models.common import utc_now
from hotel.services.phone import normalize_phone


VALID_ROLES = frozenset({'admin', 'receptionist', 'customer'})
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,59}$')


def credential_tag(password_hash: str) -> str:
    """Snapshot marker: changing a password invalidates open desktop sessions."""
    return hashlib.sha256(password_hash.encode('utf-8')).hexdigest()


def normalize_username(username: str) -> str:
    value = str(username).strip()
    if not USERNAME_PATTERN.fullmatch(value):
        raise ValueError('Tên đăng nhập phải dài 3–60 ký tự, chỉ gồm chữ không dấu, số, dấu chấm, gạch dưới hoặc gạch ngang.')
    return value


def _create_account(db, *, username, full_name, password, role, actor_id=None,
                    email=None, email_verified_at=None, phone=None,
                    must_change_password=False, temporary_password_expires_at=None):
    username = normalize_username(username)
    full_name = str(full_name).strip()
    if not 2 <= len(full_name) <= 120:
        raise ValueError('Họ tên phải dài từ 2 đến 120 ký tự.')
    if role not in VALID_ROLES:
        raise ValueError('Vai trò tài khoản không hợp lệ.')
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise ValueError('Tên đăng nhập đã tồn tại.')
    if email and db.scalar(select(User.id).where(User.email == email)) is not None:
        raise ValueError('Email đã được đăng ký.')
    if phone and db.scalar(select(User.id).where(User.phone == phone)) is not None:
        raise ValueError('Số điện thoại đã được dùng cho tài khoản khác.')
    new_user = User(username=username, full_name=full_name,
                    password_hash=hash_password(password), role=role, active=True,
                    email=email, email_verified_at=email_verified_at, phone=phone,
                    must_change_password=must_change_password,
                    temporary_password_expires_at=temporary_password_expires_at)
    db.add(new_user)
    try:
        db.flush()
        attach_role_and_employee(db, new_user)
        if role == 'customer':
            db.add(Customer(user_id=new_user.id, full_name=full_name,
                            phone=phone, email=email or ''))
        log_event(db, actor_id, 'user.register' if role == 'customer' else 'user.create', username)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError('Tên đăng nhập, email hoặc số điện thoại đã tồn tại.') from exc
    return new_user


def request_registration_otp(db, email):
    email = email_otp.normalize_email(email)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise ValueError('Email đã được đăng ký.')
    email_otp.issue_otp(db, email, 'register')


def register_customer(db, username, full_name, email, password, confirmation, otp, phone):
    if password != confirmation:
        raise ValueError('Mật khẩu xác nhận không khớp.')
    username = normalize_username(username)
    email = email_otp.normalize_email(email)
    phone = normalize_phone(phone)
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise ValueError('Tên đăng nhập đã tồn tại.')
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise ValueError('Email đã được đăng ký.')
    if db.scalar(select(User.id).where(User.phone == phone)) is not None:
        raise ValueError('Số điện thoại đã được dùng cho tài khoản khác.')
    # Validate password before consuming the one-time code.
    validate_password(password)
    email_otp.consume_otp(db, email, 'register', otp)
    return _create_account(db, username=username, full_name=full_name,
                           password=password, role='customer', email=email,
                           email_verified_at=utc_now(), phone=phone)


def create_staff(db, actor_id, username, full_name, email, phone, position, role):
    """Issue a 24-hour temporary password by Gmail (method B)."""
    if role not in {'admin', 'receptionist'}:
        raise ValueError('Admin chỉ được cấp tài khoản nhân viên.')
    username = normalize_username(username)
    email = email_otp.normalize_email(email)
    phone = normalize_phone(phone)
    position = str(position).strip()
    if not 2 <= len(str(full_name).strip()) <= 120 or not 2 <= len(position) <= 120:
        raise ValueError('Họ tên hoặc chức vụ chưa hợp lệ.')
    if db.scalar(select(User.id).where((User.username == username) |
                 (User.email == email) | (User.phone == phone))) is not None:
        raise ValueError('Tên đăng nhập, email hoặc số điện thoại đã tồn tại.')
    temporary = secrets.token_urlsafe(18)
    user = User(username=username, full_name=full_name.strip(), phone=phone,
                email=email, email_verified_at=None, role=role, active=True,
                password_hash=hash_password(temporary), must_change_password=True,
                temporary_password_expires_at=utc_now() + timedelta(hours=24))
    db.add(user)
    try:
        db.flush()
        attach_role_and_employee(db, user)
        # Production sessions use autoflush=False. Persist the new Employee
        # before querying it, otherwise the SELECT returns None on MySQL.
        db.flush()
        employee = db.scalar(select(Employee).where(Employee.user_id == user.id))
        employee.phone, employee.position = phone, position
        log_event(db, actor_id, 'staff.temporary_issued', username)
        mailer.send_email(email, '[GrandStay] Tài khoản nhân viên mới',
                          f'Xin chào {user.full_name},\n\n'
                          f'Tên đăng nhập: {username}\nMật khẩu tạm: {temporary}\n'
                          'Mật khẩu này hết hạn sau 24 giờ và phải đổi ngay lần đầu đăng nhập.\n'
                          'Không chia sẻ email/mật khẩu này. Nếu không nhận ra yêu cầu, '
                          'hãy liên hệ quản trị viên GrandStay.')
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError('Tài khoản nhân viên đã tồn tại.') from exc
    except Exception:
        db.rollback()
        raise
    return user


def reissue_staff_password(db, actor_id, user):
    if user.role not in ('admin', 'receptionist') or user.archived_at is not None:
        raise ValueError('Chỉ cấp lại mật khẩu cho nhân viên chưa lưu trữ.')
    if user.id == actor_id:
        raise ValueError('Không tự cấp lại mật khẩu tạm cho chính Admin đang đăng nhập.')
    if not user.active:
        raise ValueError('Tài khoản đang khóa; hãy mở khóa trước khi gửi mật khẩu tạm.')
    if not user.email:
        raise ValueError('Nhân viên chưa có email. Cập nhật email trước khi cấp mật khẩu tạm.')
    temporary = secrets.token_urlsafe(18)
    user.password_hash = hash_password(temporary)
    user.must_change_password = True
    user.temporary_password_expires_at = utc_now() + timedelta(hours=24)
    user.email_verified_at = None
    user.failed_login_attempts = 0
    user.login_blocked_until = None
    log_event(db, actor_id, 'staff.temporary_reissued', user.username)
    mailer.send_email(user.email, '[GrandStay] Cấp lại mật khẩu tạm',
                      f'Tên đăng nhập: {user.username}\nMật khẩu tạm mới: {temporary}\n'
                      'Hiệu lực 24 giờ. Hãy đăng nhập và đổi ngay mật khẩu.\n'
                      'Mật khẩu cũ không còn sử dụng được.')
    db.commit()


def assign_staff_email(db, actor_id, user, email):
    """Onboard legacy employees missing Gmail without exposing their old hash."""
    if user.role not in ('admin', 'receptionist') or user.id == actor_id:
        raise ValueError('Chỉ cập nhật Gmail của nhân viên khác.')
    if user.archived_at is not None:
        raise ValueError('Tài khoản đã ngừng sử dụng.')
    email = email_otp.normalize_email(email)
    owner = db.scalar(select(User.id).where(User.email == email, User.id != user.id))
    if owner is not None:
        raise ValueError('Gmail đã được đăng ký cho tài khoản khác.')
    previous = user.email if user.email_verified_at else None
    user.email = email
    user.email_verified_at = None
    # SMTP error rolls back both email change and the newly generated hash.
    reissue_staff_password(db, actor_id, user)
    if previous and previous != email:
        try:
            mailer.send_email(previous, '[GrandStay] Thay đổi email nhân viên',
                              'Quản trị viên đã thay đổi email đăng nhập tài khoản của bạn. '
                              'Nếu không đúng, hãy liên hệ khách sạn ngay.')
        except RuntimeError:
            pass


def authenticate(db, username, password):
    identifier = str(username).strip()
    if '@' in identifier:
        user = db.scalar(select(User).where(
            User.email == email_otp.normalize_email(identifier),
            User.email_verified_at.is_not(None)))
    else:
        user = db.scalar(select(User).where(User.username == identifier))
    if not user or not user.active or user.archived_at is not None:
        raise ValueError('Sai tài khoản/mật khẩu hoặc tài khoản bị khóa.')
    now = utc_now()
    if user.login_blocked_until is not None and now < user.login_blocked_until:
        raise ValueError('Đăng nhập sai nhiều lần. Vui lòng thử lại sau 15 phút.')
    if not verify_password(password, user.password_hash):
        attempts = int(user.failed_login_attempts or 0) + 1
        if attempts >= 5:
            user.failed_login_attempts = 0
            user.login_blocked_until = now + timedelta(minutes=15)
        else:
            user.failed_login_attempts = attempts
        db.commit()  # Preserve failed attempts even though the controller raises.
        raise ValueError('Sai tài khoản/mật khẩu hoặc tài khoản bị khóa.')
    user.failed_login_attempts = 0
    user.login_blocked_until = None
    if (user.must_change_password and user.temporary_password_expires_at and
            user.temporary_password_expires_at < utc_now()):
        raise ValueError('Mật khẩu tạm đã hết hạn. Vui lòng liên hệ Admin để được cấp lại.')
    if user.role not in VALID_ROLES:
        raise PermissionError('Vai trò tài khoản chưa được hỗ trợ.')
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    log_event(db, user.id, 'auth.login', user.username)
    db.commit()
    return {'id': user.id, 'name': user.full_name, 'role': user.role,
            'email': user.email, 'email_verified': user.email_verified_at is not None,
            'phone': user.phone, 'requires_password_change': bool(user.must_change_password),
            '_credential_tag': credential_tag(user.password_hash)}


def request_password_reset(db, email):
    email = email_otp.normalize_email(email)
    user = db.scalar(select(User).where(User.email == email,
                    User.email_verified_at.is_not(None), User.active.is_(True)))
    if user:
        email_otp.issue_otp(db, email, 'reset')
    # The UI must show this same response regardless of account existence.
    return 'Nếu email đã được xác minh, mã OTP sẽ được gửi đến hộp thư của bạn.'


def reset_password_with_otp(db, email, code, new_password, confirmation):
    if new_password != confirmation:
        raise ValueError('Mật khẩu mới xác nhận không khớp.')
    new_hash = hash_password(new_password)
    email = email_otp.normalize_email(email)
    user = db.scalar(select(User).where(User.email == email,
                    User.email_verified_at.is_not(None), User.active.is_(True)))
    if not user:
        raise ValueError('OTP không hợp lệ hoặc đã hết hạn.')
    email_otp.consume_otp(db, email, 'reset', code)
    user.password_hash = new_hash
    user.must_change_password = False
    user.temporary_password_expires_at = None
    user.failed_login_attempts = 0
    user.login_blocked_until = None
    log_event(db, user.id, 'auth.email_reset', user.username)
    db.commit()
    # A notification failure must not roll back an already completed reset.
    try:
        mailer.send_email(email, '[GrandStay] Mật khẩu đã thay đổi',
                          'Mật khẩu GrandStay của bạn vừa được đặt lại. '
                          'Nếu không phải bạn, hãy liên hệ quản trị viên ngay.')
    except RuntimeError:
        pass


def request_link_email(db, user, current_password, email):
    if not verify_password(current_password, user.password_hash):
        raise ValueError('Mật khẩu hiện tại không đúng.')
    email = email_otp.normalize_email(email)
    owner = db.scalar(select(User).where(User.email == email))
    if owner and owner.id != user.id:
        raise ValueError('Email đã được sử dụng bởi tài khoản khác.')
    email_otp.issue_otp(db, email, 'link')


def confirm_link_email(db, user, email, code):
    email = email_otp.normalize_email(email)
    owner = db.scalar(select(User).where(User.email == email))
    if owner and owner.id != user.id:
        raise ValueError('Email đã được sử dụng bởi tài khoản khác.')
    email_otp.consume_otp(db, email, 'link', code)
    previous = user.email if user.email_verified_at is not None else None
    user.email, user.email_verified_at = email, utc_now()
    log_event(db, user.id, 'auth.email_link', user.username)
    db.commit()
    if previous and previous != email:
        try:
            mailer.send_email(previous, '[GrandStay] Email tài khoản đã thay đổi',
                              'Email liên kết tài khoản GrandStay của bạn vừa được cập nhật. '
                              'Nếu không phải bạn, hãy báo cho quản trị viên.')
        except RuntimeError:
            pass


def change_password(db, user, old_password, new_password, confirmation):
    if new_password != confirmation:
        raise ValueError('Mật khẩu mới xác nhận không khớp.')
    if not verify_password(old_password, user.password_hash):
        raise ValueError('Mật khẩu hiện tại không đúng.')
    if old_password == new_password:
        raise ValueError('Mật khẩu mới phải khác mật khẩu hiện tại.')
    user.password_hash = hash_password(new_password)
    if user.must_change_password and user.email and user.email_verified_at is None:
        # Using the temporary password delivered to the mailbox proves that
        # this employee received the onboarding credentials there.
        user.email_verified_at = utc_now()
    user.must_change_password = False
    user.temporary_password_expires_at = None
    log_event(db, user.id, 'auth.password_change', user.username)
    db.commit()
    return credential_tag(user.password_hash)


def set_customer_phone(db, user, current_password, phone):
    if user.role != 'customer':
        raise PermissionError('Chỉ tài khoản khách được cập nhật số điện thoại ở đây.')
    if not verify_password(current_password, user.password_hash):
        raise ValueError('Mật khẩu hiện tại không đúng.')
    phone = normalize_phone(phone)
    owner = db.scalar(select(User.id).where(User.phone == phone, User.id != user.id))
    if owner is not None:
        raise ValueError('Số điện thoại đang thuộc tài khoản khác.')
    user.phone = phone
    # Keep the historic guest phone and booking provenance unchanged.
    log_event(db, user.id, 'customer.phone_update', user.username)
    db.commit()


def admin_reset_password(db, actor_id, user, new_password):
    if user.id == actor_id:
        raise ValueError('Để đổi mật khẩu của chính mình, hãy dùng Đổi mật khẩu.')
    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.login_blocked_until = None
    log_event(db, actor_id, 'auth.password_reset', user.username)
    db.commit()


def archive_user(db, actor_id, user):
    """Soft-delete only: audit and booking references remain untouched."""
    from sqlalchemy import func
    if user.id == actor_id:
        raise ValueError('Không được lưu trữ tài khoản đang sử dụng.')
    if user.archived_at is not None:
        raise ValueError('Tài khoản đã ngừng sử dụng.')
    if user.role == 'admin':
        number = db.scalar(select(func.count(User.id)).where(
            User.role == 'admin', User.active.is_(True), User.archived_at.is_(None)))
        if number <= 1:
            raise ValueError('Phải giữ lại ít nhất một Admin hoạt động.')
    user.active = False
    user.archived_at = utc_now()
    log_event(db, actor_id, 'user.archive', user.username)
    db.commit()


def delete_staff_permanently(db, actor_id, user):
    """Hard-delete a staff login and staff records without losing business data.

    Audit entries and review decisions are preserved but disconnected from the
    deleted login. Payment attribution is mandatory in the existing schema;
    deleting an employee who recorded payments is refused, not silently reassigned.
    """
    if user.role not in ('admin', 'receptionist'):
        raise PermissionError('Chỉ được xóa tài khoản nhân viên, không xóa tài khoản khách hàng.')
    if user.id == actor_id:
        raise ValueError('Không thể xóa tài khoản đang đăng nhập.')
    if user.role == 'admin' and user.active and user.archived_at is None:
        active_admins = db.scalar(select(func.count(User.id)).where(
            User.role == 'admin', User.active.is_(True), User.archived_at.is_(None)))
        if active_admins <= 1:
            raise ValueError('Cần giữ ít nhất một Admin đang hoạt động.')
    if db.scalar(select(Payment.id).where(Payment.recorded_by == user.id).limit(1)) is not None:
        raise ValueError('Nhân viên đã ghi nhận thanh toán. Không thể xóa tài khoản '
                         'vĩnh viễn vì MySQL cần giữ người lập phiếu. Hãy khóa tài khoản.')
    if db.scalar(select(Customer.id).where(Customer.user_id == user.id).limit(1)) is not None:
        raise ValueError('Tài khoản đang liên kết hồ sơ khách. Hãy kiểm tra dữ liệu trước khi xóa.')
    if db.scalar(select(CustomerLinkRequest.id).where(
            CustomerLinkRequest.user_id == user.id).limit(1)) is not None:
        raise ValueError('Tài khoản còn yêu cầu liên kết lịch sử khách. Không thể xóa trực tiếp.')

    username, old_email = user.username, user.email
    # Keep historical logs and reviews, but remove the FK to the deleted login.
    db.execute(update(AuditLog).where(AuditLog.actor_id == user.id).values(actor_id=None))
    db.execute(update(CustomerLinkRequest).where(
        CustomerLinkRequest.reviewed_by == user.id).values(reviewed_by=None))
    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    db.execute(delete(Employee).where(Employee.user_id == user.id))
    if old_email:
        db.execute(delete(EmailOtp).where(EmailOtp.email == old_email))
    db.delete(user)
    # Surface any remaining FK constraints before writing the audit entry.
    try:
        db.flush()
        log_event(db, actor_id, 'user.hard_delete', f'Đã xóa nhân viên {username}')
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError('MySQL còn dữ liệu tham chiếu tài khoản này nên không thể '
                         'xóa an toàn. Hãy khóa tài khoản hoặc liên hệ quản trị CSDL.') from exc
