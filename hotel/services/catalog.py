"""Validation and writes for catalog, customer and staff administration."""
from datetime import date
from sqlalchemy import func, select
from hotel.models.entities import Booking, Customer, HotelService, Room, RoomType, User
from hotel.services.business import log_event, money
from hotel.services.security import hash_password


def checked_name(value, minimum=2, maximum=160):
    value = str(value).strip()
    if not minimum <= len(value) <= maximum:
        raise ValueError(f'Độ dài phải từ {minimum} tới {maximum} ký tự.')
    return value


def positive_int(value, minimum=1, maximum=1000):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError('Vui lòng nhập số nguyên.') from exc
    if not minimum <= number <= maximum:
        raise ValueError(f'Giá trị phải trong khoảng {minimum}–{maximum}.')
    return number


def add_type(db, actor_id, name, capacity, price, description=''):
    name = checked_name(name, maximum=100)
    db.add(RoomType(name=name, capacity=positive_int(capacity, 1, 30),
                    nightly_price=money(price), description=str(description).strip()[:500]))
    log_event(db, actor_id, 'room_type.create', name)
    db.commit()


def edit_type(db, actor_id, room_type, capacity, price, description=''):
    room_type.capacity = positive_int(capacity, 1, 30)
    room_type.nightly_price = money(price)
    room_type.description = str(description).strip()[:500]
    log_event(db, actor_id, 'room_type.update', room_type.name)
    db.commit()


def add_room(db, actor_id, number, type_id, floor):
    number = checked_name(number, 1, 30)
    if not db.get(RoomType, int(type_id)):
        raise ValueError('Loại phòng không tồn tại.')
    db.add(Room(number=number, room_type_id=int(type_id), floor=positive_int(floor, 0, 200)))
    log_event(db, actor_id, 'room.create', number)
    db.commit()


def edit_room(db, actor_id, room, type_id, floor):
    type_id = int(type_id)
    if not db.get(RoomType, type_id):
        raise ValueError('Loại phòng không tồn tại.')
    if room.room_type_id != type_id:
        occupied = db.scalar(select(Booking.id).where(Booking.room_id == room.id,
            Booking.status.in_(('pending', 'confirmed', 'checked_in'))).limit(1))
        if occupied:
            raise ValueError('Không thể đổi loại phòng khi còn đơn hiệu lực.')
    room.room_type_id = type_id
    room.floor = positive_int(floor, 0, 200)
    log_event(db, actor_id, 'room.update', room.number)
    db.commit()


def toggle_room(db, actor_id, room):
    if room.active:
        reserved = db.scalar(select(Booking.id).where(Booking.room_id == room.id,
            Booking.status.in_(('pending', 'confirmed', 'checked_in')),
            Booking.checkout_date > date.today()).limit(1))
        if reserved:
            raise ValueError('Phòng còn lịch đặt hiệu lực, không thể tắt.')
    room.active = not room.active
    log_event(db, actor_id, 'room.toggle', room.number)
    db.commit()


def save_customer(db, actor_id, customer, name, phone, email='', document_no=''):
    name = checked_name(name)
    phone = checked_name(phone, 8, 20)
    if customer is None:
        customer = Customer()
        db.add(customer)
    customer.full_name, customer.phone = name, phone
    customer.email, customer.document_no = str(email).strip()[:160], str(document_no).strip()[:70]
    log_event(db, actor_id, 'customer.save', name)
    db.commit()


def save_service(db, actor_id, service, name, price, active=True):
    if service is None:
        service = HotelService()
        db.add(service)
    service.name = checked_name(name, 2, 130)
    service.price = money(price)
    service.active = bool(active)
    log_event(db, actor_id, 'service.save', service.name)
    db.commit()


def add_user(db, actor_id, username, name, password, role):
    if role not in ('admin', 'receptionist'):
        raise ValueError('Vai trò không hợp lệ.')
    username = checked_name(username, 3, 60)
    db.add(User(username=username, full_name=checked_name(name, 2, 120),
                password_hash=hash_password(password), role=role))
    log_event(db, actor_id, 'user.create', username)
    db.commit()


def toggle_user(db, actor_id, user):
    if user.id == actor_id:
        raise ValueError('Không thể khóa tài khoản đang sử dụng.')
    if user.active and user.role == 'admin':
        n = db.scalar(select(func.count(User.id)).where(User.role == 'admin', User.active.is_(True)))
        if n <= 1:
            raise ValueError('Phải còn ít nhất một Admin hoạt động.')
    user.active = not user.active
    log_event(db, actor_id, 'user.toggle', user.username)
    db.commit()
