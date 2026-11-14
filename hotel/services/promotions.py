"""Promotion redemption snapshots a discount on room charges only."""
from datetime import date
import re

from sqlalchemy import select

from hotel.models.entities import BookingPromotion, Invoice, Promotion, User
from hotel.services.business import log_event, money
from hotel.services.catalog import checked_name, positive_int
from hotel.services.service_orders import authorize_booking, locked_booking


def normalize_code(value):
    code = str(value).strip().upper()
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{1,31}', code):
        raise ValueError('Mã khuyến mãi cần 2–32 ký tự chữ, số, dấu gạch ngang hoặc gạch dưới.')
    return code


def save_promotion(db, actor_id, values, row_id=None):
    actor = db.get(User, actor_id)
    if (actor is None or actor.role != 'admin' or not actor.active
            or actor.archived_at is not None or actor.must_change_password):
        raise PermissionError('Chỉ Admin được quản lý khuyến mãi.')
    code = normalize_code(values['code'])
    name = checked_name(values['name'], 2, 160)
    kind = values['discount_type']
    value = money(values['value'])
    if kind not in ('percent', 'fixed') or value <= 0 or (kind == 'percent' and value > 100):
        raise ValueError('Giảm phần trăm phải trong khoảng 0–100; mức giảm phải lớn hơn 0.')
    try:
        starts, ends = date.fromisoformat(values['starts_on']), date.fromisoformat(values['ends_on'])
    except (ValueError, TypeError) as exc:
        raise ValueError('Ngày khuyến mãi cần có dạng YYYY-MM-DD.') from exc
    if starts > ends:
        raise ValueError('Ngày kết thúc khuyến mãi phải từ ngày bắt đầu trở đi.')
    limit = positive_int(values['usage_limit'], 1, 1000000)
    duplicate = db.scalar(select(Promotion.id).where(Promotion.code == code, Promotion.id != (row_id or 0)))
    if duplicate:
        raise ValueError('Mã khuyến mãi đã tồn tại.')
    promotion = None
    if row_id:
        promotion = db.scalar(select(Promotion).where(Promotion.id == int(row_id)).with_for_update())
        if promotion is None:
            raise ValueError('Khuyến mãi không tồn tại.')
        if promotion.used_count and promotion.code != code:
            raise ValueError('Mã đã có lượt sử dụng, không thể đổi mã.')
        if limit < promotion.used_count:
            raise ValueError('Giới hạn không được thấp hơn số lượt đã sử dụng.')
    else:
        promotion = Promotion(used_count=0)
        db.add(promotion)
    promotion.code, promotion.name = code, name
    promotion.discount_type, promotion.value = kind, value
    promotion.minimum_amount = money(values.get('minimum_amount', 0))
    promotion.starts_on, promotion.ends_on = starts, ends
    promotion.usage_limit, promotion.active = limit, bool(values.get('active', True))
    log_event(db, actor_id, 'promotion.save', code)
    db.commit()
    return promotion.id


def redeem(db, booking_id, code, actor_id=None, *, commit=True):
    booking = locked_booking(db, booking_id)
    if actor_id is not None:
        authorize_booking(db, booking, actor_id)
    code = normalize_code(code)
    previous = db.scalar(select(BookingPromotion).where(
        BookingPromotion.booking_id == booking.id).with_for_update())
    if previous:
        if previous.code == code:
            return previous.discount_amount
        raise ValueError('Mỗi đơn đặt phòng chỉ áp dụng một mã khuyến mãi.')
    if booking.status not in ('pending', 'confirmed', 'checked_in'):
        raise ValueError('Đơn đặt phòng không còn hiệu lực để áp dụng khuyến mãi.')
    if db.scalar(select(Invoice.id).where(Invoice.booking_id == booking.id).with_for_update()):
        raise ValueError('Hóa đơn đã chốt, không thể áp dụng khuyến mãi.')
    promotion = db.scalar(select(Promotion).where(Promotion.code == code).with_for_update())
    today = date.today()
    if (promotion is None or not promotion.active
            or not promotion.starts_on <= today <= promotion.ends_on):
        raise ValueError('Mã khuyến mãi không tồn tại, chưa hiệu lực hoặc đã hết hạn.')
    if promotion.used_count >= promotion.usage_limit:
        raise ValueError('Mã khuyến mãi đã hết lượt sử dụng.')
    room_amount = booking.nightly_price * (booking.checkout_date - booking.checkin_date).days
    if room_amount < promotion.minimum_amount:
        raise ValueError('Tiền phòng chưa đạt mức tối thiểu của chương trình.')
    discount = promotion.value
    if promotion.discount_type == 'percent':
        discount = money(room_amount * promotion.value / 100)
    discount = min(room_amount, discount)
    db.add(BookingPromotion(booking_id=booking.id, promotion_id=promotion.id,
        code=code, discount_amount=discount, applied_by=actor_id))
    promotion.used_count += 1
    log_event(db, actor_id, 'promotion.apply', f'{booking.code}: {code}')
    if commit:
        db.commit()
    return discount
