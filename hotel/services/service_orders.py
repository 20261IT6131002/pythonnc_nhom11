"""Service requests reserve capacity and post one usage only on completion."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from hotel.models.common import utc_now
from hotel.models.entities import (Booking, BookingPromotion, Customer, HotelService, Invoice, ServiceDetails,
                                   ServiceOrder, ServiceUsage, SystemSetting, User)
from hotel.repositories.services import ServiceRepository
from hotel.services.business import effective_booking_status, log_event
from hotel.services.catalog import checked_name, positive_int


HOTEL_TIMEZONE = timezone(timedelta(hours=7))
OPEN_STATUSES = ('pending', 'confirmed')


def local_timestamp(value):
    if value is None:
        return ''
    return value.replace(tzinfo=timezone.utc).astimezone(HOTEL_TIMEZONE).strftime('%Y-%m-%d %H:%M')


def order_filters(query='', status='', date_from='', date_to=''):
    query = checked_name(query, 0, 160)
    if status not in ('', 'pending', 'confirmed', 'completed', 'cancelled'):
        raise ValueError('Trạng thái yêu cầu dịch vụ không hợp lệ.')
    bounds = []
    for value, day_time in ((date_from, time.min), (date_to, time.max)):
        if not str(value).strip():
            bounds.append(None)
            continue
        try:
            day = date.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValueError('Ngày lọc cần có dạng YYYY-MM-DD.') from exc
        if day.year < 1000:
            raise ValueError('Năm lọc cần từ 1000 trở đi.')
        bounds.append(datetime.combine(day, day_time, tzinfo=HOTEL_TIMEZONE)
                      .astimezone(timezone.utc).replace(tzinfo=None))
    if bounds[0] and bounds[1] and bounds[0] > bounds[1]:
        raise ValueError('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')
    return dict(query=query, status=status, created_from=bounds[0], created_until=bounds[1])


def booking_details(db, booking, actor_id):
    """Read the full service ledger, including legacy usages, without issuing an invoice."""
    authorize_booking(db, booking, actor_id)
    repo = ServiceRepository(db)
    orders = repo.booking_orders(booking.id)
    usages = repo.booking_usages(booking.id)
    linked_usage_ids = {order.usage_id for order in orders if order.usage_id is not None}
    rows = [{'id': f'order-{order.id}', 'source': f'Yêu cầu #{order.id}',
             'service': order.service_name, 'quantity': order.quantity,
             'unit_price': order.unit_price, 'amount': order.unit_price * order.quantity,
             'status': order.status, 'created_at': local_timestamp(order.created_at),
             'scheduled_at': str(order.scheduled_at or ''), 'notes': order.notes} for order in orders]
    rows.extend({'id': f'usage-{usage.id}', 'source': 'Phát sinh trực tiếp',
                 'service': usage.service.name, 'quantity': usage.quantity,
                 'unit_price': usage.unit_price, 'amount': usage.unit_price * usage.quantity,
                 'status': 'completed', 'created_at': local_timestamp(usage.created_at),
                 'scheduled_at': '', 'notes': ''} for usage in usages if usage.id not in linked_usage_ids)
    service_total = sum((usage.unit_price * usage.quantity for usage in usages), Decimal('0'))
    open_total = sum((order.unit_price * order.quantity for order in orders
                      if order.status in OPEN_STATUSES), Decimal('0'))
    room_total = booking.nightly_price * (booking.checkout_date - booking.checkin_date).days
    promotion = db.get(BookingPromotion, booking.id)
    discount = min(room_total, promotion.discount_amount) if promotion else Decimal('0')
    invoice = booking.invoice
    if invoice is not None:
        room_total, service_total, discount = invoice.room_amount, invoice.services_amount, invoice.discount_amount
        total = invoice.total_amount
        paid = sum((payment.amount for payment in invoice.payments), Decimal('0'))
    else:
        total, paid = room_total + service_total - discount, Decimal('0')
    return {'booking_id': booking.id, 'code': booking.code, 'room': booking.room.number,
            'customer': booking.customer.full_name, 'status': effective_booking_status(booking),
            'rows': rows, 'room_total': room_total, 'service_total': service_total,
            'open_total': open_total, 'discount': discount, 'total': total, 'paid': paid,
            'due': max(Decimal('0'), total - paid), 'invoice_id': invoice.id if invoice else None}


def authorize_booking(db, booking, actor_id):
    actor = db.get(User, actor_id)
    if actor is None or not actor.active or actor.archived_at is not None or actor.must_change_password:
        raise PermissionError('Tài khoản không có quyền sử dụng chức năng này.')
    if actor.role in ('admin', 'receptionist'):
        return actor
    customer = db.get(Customer, booking.customer_id)
    if actor.role != 'customer' or customer.user_id != actor.id:
        raise PermissionError('Bạn chỉ được thao tác trên đặt phòng của mình.')
    return actor


def locked_booking(db, booking_id):
    booking = db.scalar(select(Booking).where(Booking.id == int(booking_id))
                        .with_for_update().execution_options(populate_existing=True))
    if booking is None:
        raise ValueError('Đơn đặt phòng không tồn tại.')
    return booking


def require_open_stay(db, booking):
    if booking.status != 'checked_in':
        raise ValueError('Chỉ đăng ký dịch vụ khi đã nhận phòng.')
    if db.scalar(select(Invoice.id).where(Invoice.booking_id == booking.id).with_for_update()):
        raise ValueError('Hóa đơn đã chốt, không thể thay đổi dịch vụ.')


def details_values(details):
    if details is None:
        return {'category': 'Tiện ích', 'unit': 'lượt', 'description': '',
                'requires_schedule': False, 'duration_minutes': 60, 'slot_capacity': 1}
    return {key: getattr(details, key) for key in
            ('category', 'unit', 'description', 'requires_schedule', 'duration_minutes', 'slot_capacity')}


def update_details(db, service, values):
    details = db.scalar(select(ServiceDetails).where(ServiceDetails.service_id == service.id).with_for_update())
    existing = details_values(details)
    if details is None:
        details = ServiceDetails(service_id=service.id)
        db.add(details)
    # Existing requests keep their own price and duration snapshots.
    for field, maximum in (('category', 80), ('unit', 40), ('description', 500)):
        if field in values:
            setattr(details, field, checked_name(values[field], 0 if field == 'description' else 1, maximum))
    if 'requires_schedule' in values:
        details.requires_schedule = bool(values['requires_schedule'])
    if 'duration_minutes' in values:
        details.duration_minutes = positive_int(values['duration_minutes'], 1, 1440)
    if 'slot_capacity' in values:
        capacity = positive_int(values['slot_capacity'], 1, 1000)
        if capacity < existing['slot_capacity']:
            pending = db.scalar(select(ServiceOrder.id).where(
                ServiceOrder.service_id == service.id, ServiceOrder.status.in_(OPEN_STATUSES),
                ServiceOrder.scheduled_at.is_not(None)).limit(1).with_for_update())
            if pending:
                raise ValueError('Còn lịch dịch vụ hiệu lực, chưa thể giảm sức chứa.')
        details.slot_capacity = capacity


def parse_schedule(value):
    if not value:
        return None
    try:
        start = datetime.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValueError('Dịch vụ cần lịch hẹn dạng YYYY-MM-DD HH:MM.') from exc
    if start.tzinfo is not None:
        start = start.astimezone(HOTEL_TIMEZONE).replace(tzinfo=None)
    return start


def schedule_interval(booking, details, scheduled_at, checkout_time='12:00'):
    start = parse_schedule(scheduled_at)
    if not details or not details.requires_schedule:
        if start:
            raise ValueError('Dịch vụ này không sử dụng lịch hẹn.')
        return None, None
    if start is None:
        raise ValueError('Dịch vụ này cần nhập lịch hẹn.')
    end = start + timedelta(minutes=details.duration_minutes)
    now = datetime.now(HOTEL_TIMEZONE).replace(tzinfo=None)
    if start < now:
        raise ValueError('Lịch hẹn phải ở thời điểm tương lai.')
    if (start < datetime.combine(booking.checkin_date, time.min)
            or end > datetime.combine(booking.checkout_date, time.fromisoformat(checkout_time))):
        raise ValueError('Lịch dịch vụ phải nằm trong thời gian lưu trú đã đặt.')
    return start, end


def request_service(db, booking_id, service_id, quantity, actor_id, *, scheduled_at='', notes='', request_token=None):
    booking = locked_booking(db, booking_id)
    authorize_booking(db, booking, actor_id)
    token = checked_name(request_token or uuid4().hex, 1, 64)
    previous = db.scalar(select(ServiceOrder).where(ServiceOrder.request_token == token).with_for_update())
    quantity = positive_int(quantity, 1, 1000)
    notes = checked_name(notes, 0, 500)
    if previous:
        if (previous.booking_id != booking.id or previous.service_id != int(service_id)
                or previous.quantity != quantity or previous.requested_by != actor_id
                or previous.scheduled_at != parse_schedule(scheduled_at) or previous.notes != notes):
            raise ValueError('Mã yêu cầu đã được sử dụng cho nội dung khác.')
        return previous.id
    require_open_stay(db, booking)
    # All reservations for a service serialize on its catalog row, even across bookings.
    service = db.scalar(select(HotelService).where(HotelService.id == int(service_id)).with_for_update())
    if service is None or not service.active:
        raise ValueError('Dịch vụ không tồn tại hoặc đã ngừng cung cấp.')
    details = db.scalar(select(ServiceDetails).where(ServiceDetails.service_id == service.id).with_for_update())
    checkout_setting = db.get(SystemSetting, 'checkout_time')
    start, end = schedule_interval(booking, details, scheduled_at,
                                  checkout_setting.value if checkout_setting else '12:00')
    if start:
        overlapping = db.scalars(select(ServiceOrder).where(
            ServiceOrder.service_id == service.id, ServiceOrder.status.in_(OPEN_STATUSES),
            ServiceOrder.scheduled_at < end, ServiceOrder.scheduled_until > start)
            .with_for_update()).all()
        # Check peak occupancy, allowing consecutive appointments in the requested interval.
        events = [(start, quantity), (end, -quantity)]
        for order in overlapping:
            events.extend([(max(start, order.scheduled_at), order.quantity),
                           (min(end, order.scheduled_until), -order.quantity)])
        occupied = 0
        for _, delta in sorted(events):
            occupied += delta
            if occupied > details.slot_capacity:
                raise ValueError('Khung giờ dịch vụ đã đủ suất phục vụ.')
    order = ServiceOrder(booking_id=booking.id, service_id=service.id,
        service_name=service.name, quantity=quantity, unit_price=service.price,
        scheduled_at=start, scheduled_until=end, requested_by=actor_id,
        request_token=token, notes=notes)
    db.add(order)
    log_event(db, actor_id, 'service.request', booking.code)
    db.commit()
    return order.id


def change_status(db, order_id, status, actor_id):
    original = db.get(ServiceOrder, int(order_id))
    if original is None:
        raise ValueError('Yêu cầu dịch vụ không tồn tại.')
    booking = locked_booking(db, original.booking_id)
    actor = authorize_booking(db, booking, actor_id)
    order = db.scalar(select(ServiceOrder).where(ServiceOrder.id == original.id)
                      .with_for_update().execution_options(populate_existing=True))
    if actor.role == 'customer' and (status != 'cancelled' or order.status not in ('pending', 'cancelled')):
        raise PermissionError('Khách chỉ được hủy yêu cầu đang chờ xác nhận.')
    if order.status == status:
        return order.usage_id
    if status not in {'pending': {'confirmed', 'cancelled'},
                     'confirmed': {'completed', 'cancelled'}}.get(order.status, set()):
        raise ValueError('Không được chuyển trạng thái dịch vụ theo yêu cầu.')
    require_open_stay(db, booking)
    if status == 'confirmed':
        order.confirmed_by = actor_id
    if status == 'completed':
        usage = ServiceUsage(booking_id=booking.id, service_id=order.service_id,
                             quantity=order.quantity, unit_price=order.unit_price)
        db.add(usage)
        db.flush()
        order.usage_id = usage.id
        order.completed_at = utc_now()
    order.status = status
    log_event(db, actor_id, 'service.order_status', f'{order.id}: {status}')
    db.commit()
    return order.usage_id
