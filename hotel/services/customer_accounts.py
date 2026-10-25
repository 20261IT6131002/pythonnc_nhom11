"""Customer account links: phone lookup proposes, staff approval proves.

A phone number or booking code alone must never grant access to all stay history.
"""
from sqlalchemy import select

from hotel.models.entities import Booking, Customer, CustomerLinkRequest, User
from hotel.models.common import utc_now
from hotel.services.business import log_event
from hotel.services.phone import normalize_phone, phones_match


def history(db, user):
    if user.role != 'customer':
        raise PermissionError('Chỉ tài khoản khách hàng được xem lịch sử của mình.')
    records = db.scalars(select(Booking).join(Customer).where(
        Customer.user_id == user.id).order_by(Booking.id.desc()).limit(100)).all()
    return [{'code': b.code, 'room': b.room.number,
             'checkin': str(b.checkin_date), 'checkout': str(b.checkout_date),
             'status': b.status, 'customer': b.customer.full_name} for b in records]


def request_link(db, user, booking_code, phone):
    if user.role != 'customer' or not user.phone:
        raise PermissionError('Cần đăng nhập tài khoản khách có số điện thoại.')
    if normalize_phone(phone) != user.phone:
        raise ValueError('Số điện thoại không trùng với tài khoản của bạn.')
    code = str(booking_code).strip().upper()
    booking = db.scalar(select(Booking).where(Booking.code == code))
    if not booking or not phones_match(booking.customer.phone, phone):
        raise ValueError('Không tìm thấy mã đặt phòng khớp với SĐT đã nhập.')
    customer = booking.customer
    if customer.user_id == user.id:
        raise ValueError('Lịch sử này đã thuộc tài khoản của bạn.')
    if customer.user_id is not None:
        raise ValueError('Hồ sơ đã được liên kết. Hãy liên hệ lễ tân để được hỗ trợ.')
    previous = db.scalar(select(CustomerLinkRequest.id).where(
        CustomerLinkRequest.user_id == user.id,
        CustomerLinkRequest.customer_id == customer.id,
        CustomerLinkRequest.status == 'pending'))
    if previous:
        raise ValueError('Bạn đã có yêu cầu đang chờ nhân viên xác minh.')
    db.add(CustomerLinkRequest(user_id=user.id, customer_id=customer.id,
                               booking_code=code, status='pending'))
    log_event(db, user.id, 'customer.link_request', code)
    db.commit()


def pending_requests(db):
    rows = db.scalars(select(CustomerLinkRequest).where(
        CustomerLinkRequest.status == 'pending').order_by(
        CustomerLinkRequest.id.desc()).limit(200)).all()
    return [{'id': row.id, 'user_id': row.user_id,
             'username': db.get(User, row.user_id).username,
             'customer_id': row.customer_id,
             'customer': db.get(Customer, row.customer_id).full_name,
             'code': row.booking_code, 'status': row.status} for row in rows]


def decide_link(db, actor_id, row_id, approve):
    row = db.scalar(select(CustomerLinkRequest).where(
        CustomerLinkRequest.id == int(row_id)).with_for_update())
    if row is None or row.status != 'pending':
        raise ValueError('Yêu cầu không còn ở trạng thái chờ.')
    customer = db.scalar(select(Customer).where(
        Customer.id == row.customer_id).with_for_update())
    if customer is None:
        raise ValueError('Hồ sơ khách không tồn tại.')
    if approve:
        if customer.user_id not in (None, row.user_id):
            raise ValueError('Hồ sơ đã liên kết với tài khoản khác.')
        customer.user_id = row.user_id
    row.status = 'approved' if approve else 'rejected'
    row.reviewed_at = utc_now()
    row.reviewed_by = actor_id
    log_event(db, actor_id, 'customer.link_decision',
              f'Yêu cầu {row.id}: {row.status}, customer_id={customer.id}')
    db.commit()
