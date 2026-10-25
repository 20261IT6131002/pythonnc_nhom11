"""N1 account role/employee records and hotel configuration."""
from __future__ import annotations

import os

from sqlalchemy import select

from hotel.models.entities import Employee, Role, SystemSetting, User, UserRole
from hotel.services.business import log_event
from hotel.services.phone import normalize_phone


ROLE_NAMES = {
    'admin': 'Quản trị viên',
    'receptionist': 'Nhân viên lễ tân',
    'customer': 'Khách hàng',
}

SETTING_FIELDS = {
    'hotel_name': ('Tên khách sạn', 120),
    'hotel_address': ('Địa chỉ', 250),
    'hotel_phone': ('Số điện thoại', 30),
    'checkin_time': ('Giờ nhận phòng', 5),
    'checkout_time': ('Giờ trả phòng', 5),
}


def _role(db, code):
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        role = Role(code=code, name=ROLE_NAMES[code])
        db.add(role)
        db.flush()
    return role


def attach_role_and_employee(db, user):
    if user.role not in ROLE_NAMES:
        return
    role = _role(db, user.role)
    exists = db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id))
    if exists is None:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    if user.role in {'admin', 'receptionist'} and db.scalar(
        select(Employee.id).where(Employee.user_id == user.id)) is None:
        db.add(Employee(user_id=user.id, position=ROLE_NAMES[user.role]))


def bootstrap_n1(db):
    """Idempotently add new N1 tables' reference rows for old MySQL installations."""
    for code in ROLE_NAMES:
        _role(db, code)
    for user in db.scalars(select(User)).all():
        attach_role_and_employee(db, user)
    if db.get(SystemSetting, 'hotel_name') is None:
        db.add(SystemSetting(key='hotel_name', value=os.getenv('HOTEL_NAME', 'GrandStay')))
    for key, default in {'hotel_address': '', 'hotel_phone': '',
                         'checkin_time': '14:00', 'checkout_time': '12:00'}.items():
        if db.get(SystemSetting, key) is None:
            db.add(SystemSetting(key=key, value=default))
    db.commit()


def get_settings(db):
    rows = db.scalars(select(SystemSetting)).all()
    return {row.key: row.value for row in rows}


def update_settings(db, actor_id, values):
    for key, (_, max_length) in SETTING_FIELDS.items():
        if key not in values:
            continue
        value = str(values[key]).strip()
        if len(value) > max_length:
            raise ValueError(f'{SETTING_FIELDS[key][0]} tối đa {max_length} ký tự.')
        if key in ('checkin_time', 'checkout_time'):
            from datetime import time
            try:
                time.fromisoformat(value)
            except ValueError as exc:
                raise ValueError('Giờ nhận/trả phòng cần có dạng HH:MM.') from exc
        if key == 'hotel_name' and not value:
            raise ValueError('Tên khách sạn không được để trống.')
        setting = db.get(SystemSetting, key)
        if setting is None:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)
        else:
            setting.value = value
    log_event(db, actor_id, 'system_settings.update', 'Thông tin khách sạn')
    db.commit()


def save_employee(db, actor_id, user, phone, position):
    if user.role not in {'admin', 'receptionist'}:
        raise ValueError('Chỉ có thể cập nhật hồ sơ nhân viên.')
    phone, position = str(phone).strip(), str(position).strip()
    if len(phone) > 20 or not 2 <= len(position) <= 120:
        raise ValueError('Số điện thoại hoặc chức vụ chưa hợp lệ.')
    if phone:
        normalized = normalize_phone(phone)
        owner = db.scalar(select(User.id).where(User.phone == normalized,
                                               User.id != user.id))
        if owner is not None:
            raise ValueError('Số điện thoại đã được sử dụng ở tài khoản khác.')
        user.phone = normalized
    employee = db.scalar(select(Employee).where(Employee.user_id == user.id))
    if employee is None:
        employee = Employee(user_id=user.id)
        db.add(employee)
    employee.phone, employee.position = user.phone or '', position
    log_event(db, actor_id, 'employee.update', user.username)
    db.commit()
