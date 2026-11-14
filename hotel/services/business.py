from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from hotel.models.entities import (Booking, Room, RoomType, Customer, HotelService, ServiceUsage, Invoice, Payment, AuditLog, utc_now)

ACTIVE_STATUSES = ('pending', 'confirmed', 'checked_in')

def money(value):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError('Số tiền không hợp lệ.')
    if not d.is_finite() or d < 0:
        raise ValueError('Số tiền không hợp lệ.')
    return d.quantize(Decimal('0.01'))

def dates_in_order(checkin, checkout):
    if not isinstance(checkin, date) or not isinstance(checkout, date) or checkin >= checkout:
        raise ValueError('Ngày trả phòng phải sau ngày nhận phòng.')
    if checkin < date.today():
        raise ValueError('Ngày nhận phòng không được trong quá khứ.')

def conflicting_query(room_id, checkin, checkout):
    return select(Booking.id).where(Booking.room_id == room_id, Booking.status.in_(ACTIVE_STATUSES), Booking.checkin_date < checkout, Booking.checkout_date > checkin)

def find_rooms(db: Session, checkin=None, checkout=None, room_type_id=None, guests=1):
    q = select(Room).join(RoomType).options(joinedload(Room.room_type)).where(Room.active.is_(True), RoomType.capacity >= guests).order_by(Room.number)
    if room_type_id:
        q = q.where(Room.room_type_id == room_type_id)
    rooms = db.scalars(q).all()
    if checkin and checkout:
        dates_in_order(checkin, checkout)
        rooms = [r for r in rooms if db.scalar(conflicting_query(r.id, checkin, checkout)) is None]
    return rooms

def log_event(db, actor_id, action, details=''):
    db.add(AuditLog(actor_id=actor_id, action=action, details=str(details)[:300]))

def create_booking(db: Session, *, name, phone, email, room_id, checkin, checkout, guests, notes='', status='pending', actor_id=None, customer_id=None, promotion_code=''):
    dates_in_order(checkin, checkout)
    name, phone = str(name).strip(), str(phone).strip()
    if len(name) < 2 or not 8 <= len(phone) <= 20:
        raise ValueError('Tên hoặc số điện thoại chưa hợp lệ.')
    if guests < 1 or guests > 30:
        raise ValueError('Số khách không hợp lệ.')
    if status not in ('pending','confirmed'):
        raise ValueError('Trạng thái không hợp lệ.')
    # Trên MySQL, khóa dòng phòng để tuần tự hóa các đặt phòng cùng phòng.
    # Cần tất cả các nơi tạo đặt phòng đều sử dụng nghiệp vụ này.
    room = db.scalar(select(Room).where(Room.id == room_id).with_for_update())
    if room is None or not room.active:
        raise ValueError('Phòng không tồn tại hoặc đã ngừng hoạt động.')
    if guests > room.room_type.capacity:
        raise ValueError('Số khách vượt quá sức chứa của phòng.')
    if db.scalar(conflicting_query(room.id, checkin, checkout)) is not None:
        raise ValueError('Phòng đã có đơn đặt trùng khoảng thời gian này.')
    # Do not attach an anonymous booking to an existing profile just because
    # someone knows the other person's name and phone number.
    customer = db.get(Customer, int(customer_id)) if customer_id else None
    if customer_id and customer is None:
        raise ValueError('Hồ sơ khách được chọn không tồn tại.')
    if customer is None:
        customer = Customer(full_name=name, phone=phone, email=email.strip())
        db.add(customer)
        db.flush()
    booking = Booking(code='BK-'+uuid4().hex[:10].upper(), customer_id=customer.id, room_id=room.id,
        checkin_date=checkin, checkout_date=checkout, guests=guests, nightly_price=room.room_type.nightly_price,
        notes=notes.strip()[:1000], status=status)
    db.add(booking)
    if str(promotion_code).strip():
        from hotel.services.promotions import redeem

        db.flush()
        redeem(db, booking.id, promotion_code, actor_id, commit=False)
    log_event(db, actor_id, 'booking.create', booking.code)
    db.commit()
    db.refresh(booking)
    return booking

def change_booking_status(db, booking, new_status, actor_id):
    transitions={'pending':{'confirmed','cancelled'}, 'confirmed':{'checked_in','cancelled'}, 'checked_in':{'checked_out'}, 'checked_out':set(), 'cancelled':set()}
    if new_status not in transitions.get(booking.status, set()):
        raise ValueError('Không được chuyển trạng thái theo yêu cầu.')
    if new_status == 'checked_out':
        if booking.invoice is None:
            raise ValueError('Cần lập hóa đơn và ghi nhận thanh toán trước khi trả phòng.')
        if invoice_due(booking.invoice) > 0:
            raise ValueError('Cần thanh toán đủ hóa đơn trước khi trả phòng.')
        booking.checked_out_at = utc_now()
    elif new_status == 'checked_in':
        booking.checked_in_at = utc_now()
    booking.status = new_status
    log_event(db, actor_id, 'booking.status', f'{booking.code}: {new_status}')
    db.commit()

def add_service_usage(db, booking, service, quantity, actor_id):
    from hotel.models.customer_services import ServiceDetails
    from hotel.services.service_orders import locked_booking

    booking = locked_booking(db, booking.id)
    service = db.scalar(select(HotelService).where(HotelService.id == service.id)
                        .with_for_update().execution_options(populate_existing=True))
    details = db.scalar(select(ServiceDetails).where(ServiceDetails.service_id == service.id).with_for_update())
    if details and details.requires_schedule:
        raise ValueError('Dịch vụ có lịch hẹn cần tạo yêu cầu và xác nhận trước khi hoàn thành.')
    if booking.status != 'checked_in':
        raise ValueError('Chỉ thêm dịch vụ cho khách đã nhận phòng.')
    if not service.active or quantity < 1 or quantity > 1000:
        raise ValueError('Dịch vụ hoặc số lượng không hợp lệ.')
    if booking.invoice is not None:
        raise ValueError('Hóa đơn đã chốt, không thể thêm dịch vụ.')
    db.add(ServiceUsage(booking_id=booking.id, service_id=service.id, quantity=quantity, unit_price=service.price))
    log_event(db, actor_id, 'service.usage', booking.code)
    db.commit()

def invoice_due(invoice):
    paid = sum((p.amount for p in invoice.payments), Decimal('0'))
    return max(Decimal('0'), invoice.total_amount - paid)

def ensure_invoice(db,booking,actor_id=None):
    from hotel.models.customer_services import BookingPromotion, ServiceOrder
    from hotel.services.customers import snapshot_invoice_customer
    from hotel.services.service_orders import locked_booking

    booking = locked_booking(db, booking.id)
    if booking.status not in ('checked_in', 'checked_out'):
        raise ValueError('Chỉ lập hóa đơn cho khách đã nhận phòng.')
    existing = db.scalar(select(Invoice).where(Invoice.booking_id == booking.id).with_for_update())
    if existing is not None:
        return existing
    outstanding = db.scalar(select(ServiceOrder.id).where(ServiceOrder.booking_id == booking.id,
        ServiceOrder.status.in_(('pending', 'confirmed'))).limit(1).with_for_update())
    if outstanding:
        raise ValueError('Còn yêu cầu dịch vụ chưa hoàn thành hoặc hủy; cần xử lý trước khi chốt hóa đơn.')
    nights=(booking.checkout_date-booking.checkin_date).days
    room_amount=booking.nightly_price * nights
    usages = db.scalars(select(ServiceUsage).where(ServiceUsage.booking_id == booking.id).with_for_update()).all()
    services_amount=sum((u.unit_price*u.quantity for u in usages), Decimal('0'))
    promotion = db.scalar(select(BookingPromotion).where(BookingPromotion.booking_id == booking.id).with_for_update())
    discount = min(room_amount, promotion.discount_amount) if promotion else Decimal('0')
    invoice=Invoice(booking_id=booking.id,room_amount=room_amount,services_amount=services_amount,total_amount=room_amount+services_amount-discount, discount_amount=discount)
    db.add(invoice)
    db.flush()
    customer = db.scalar(select(Customer).where(Customer.id == booking.customer_id).with_for_update())
    snapshot_invoice_customer(db, invoice, customer)
    log_event(db, actor_id, 'invoice.create', booking.code)
    db.commit()
    db.refresh(invoice)
    return invoice

def record_payment(db, invoice, amount, method, reference, actor_id):
    # Khóa hóa đơn để tránh hai thao tác ghi nhận đồng thời vượt số tiền cần thu (MySQL/InnoDB).
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice.id).with_for_update())
    amount=money(amount)
    if amount <= 0 or amount > invoice_due(invoice):
        raise ValueError('Số tiền phải lớn hơn 0 và không vượt số tiền còn thiếu.')
    if method not in {'cash','bank_transfer','card_manual'}:
        raise ValueError('Phương thức thanh toán không hợp lệ.')
    db.add(Payment(invoice_id=invoice.id, amount=amount, method=method, reference=str(reference)[:100], recorded_by=actor_id))
    log_event(db,actor_id,'payment.record',f'{invoice.id} - {amount}')
    db.commit()

def revenue_summary(db,date_from,date_to):
    if date_from>date_to:
        raise ValueError('Ngày bắt đầu phải trước ngày kết thúc.')
    payments=db.scalars(select(Payment).where(func.date(Payment.created_at)>=date_from.isoformat(),func.date(Payment.created_at)<=date_to.isoformat()).order_by(Payment.created_at.desc())).all()
    return payments,sum((p.amount for p in payments),Decimal('0'))
