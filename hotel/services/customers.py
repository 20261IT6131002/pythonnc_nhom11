"""Profile updates and accompanying guests, independent of N1 account linking."""
from datetime import date

from sqlalchemy import select

from hotel.models.entities import (Booking, BookingGuest, Customer, CustomerProfile,
                                   Invoice, InvoiceCustomerSnapshot)
from hotel.services.business import log_event
from hotel.services.catalog import checked_name


CATEGORY_NAMES = {'normal': 'Khách mới', 'regular': 'Khách quen', 'vip': 'VIP',
                  'corporate': 'Doanh nghiệp', 'group': 'Khách đoàn'}


def optional_birth_date(value):
    if not value:
        return None
    try:
        result = date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError('Ngày sinh cần có dạng YYYY-MM-DD.') from exc
    if result > date.today():
        raise ValueError('Ngày sinh không được ở tương lai.')
    return result


def profile_values(profile):
    if profile is None:
        return {'category': 'normal', 'address': '', 'birth_date': '', 'organization': '',
                'preferences': '', 'special_requests': ''}
    return {key: str(getattr(profile, key) or '') for key in
            ('category', 'address', 'birth_date', 'organization', 'preferences', 'special_requests')}


def update_profile(db, customer, values, *, allow_category=True):
    profile = db.scalar(select(CustomerProfile).where(CustomerProfile.customer_id == customer.id).with_for_update())
    if profile is None:
        profile = CustomerProfile(customer_id=customer.id, category='normal')
        db.add(profile)
    if allow_category and 'category' in values:
        if values['category'] not in CATEGORY_NAMES:
            raise ValueError('Phân loại khách không hợp lệ.')
        profile.category = values['category']
    for field, maximum in (('address', 250), ('organization', 160),
                           ('preferences', 1000), ('special_requests', 1000)):
        if field in values:
            value = str(values[field]).strip()
            if len(value) > maximum:
                raise ValueError(f'Thông tin hồ sơ vượt quá {maximum} ký tự.')
            setattr(profile, field, value)
    if 'birth_date' in values:
        profile.birth_date = optional_birth_date(values['birth_date'])
    return profile


def snapshot_invoice_customer(db, invoice, customer):
    if db.get(InvoiceCustomerSnapshot, invoice.id) is None:
        db.add(InvoiceCustomerSnapshot(invoice_id=invoice.id, full_name=customer.full_name,
            phone=customer.phone, email=customer.email, document_no=customer.document_no))


def preserve_invoice_customers(db, customer):
    # Capture legacy invoices before the first profile edit after installing N3.
    invoices = db.scalars(select(Invoice).join(Booking)
        .where(Booking.customer_id == customer.id)).all()
    for invoice in invoices:
        snapshot_invoice_customer(db, invoice, customer)


def save_booking_guest(db, booking, values, actor_id, guest_id=None):
    if booking.status not in ('pending', 'confirmed', 'checked_in'):
        raise ValueError('Chỉ cập nhật người lưu trú cho đơn còn hiệu lực.')
    rows = db.scalars(select(BookingGuest).where(BookingGuest.booking_id == booking.id)
                      .with_for_update()).all()
    guest = next((row for row in rows if row.id == guest_id), None)
    if guest_id is not None and guest is None:
        raise ValueError('Người lưu trú không thuộc đơn đặt phòng này.')
    if guest is None:
        if len(rows) >= min(booking.guests, booking.room.room_type.capacity):
            raise ValueError('Danh sách người lưu trú đã đủ số khách của đơn đặt phòng.')
        guest = BookingGuest(booking_id=booking.id)
        db.add(guest)
    guest.full_name = checked_name(values['name'], 2, 160)
    guest.document_no = checked_name(values.get('document_no', ''), 0, 70)
    guest.birth_date = optional_birth_date(values.get('birth_date', ''))
    guest.nationality = checked_name(values.get('nationality', 'Việt Nam'), 1, 80)
    guest.is_primary = bool(values.get('is_primary', False))
    if guest.is_primary:
        for other in rows:
            if other is not guest:
                other.is_primary = False
    log_event(db, actor_id, 'booking.guest_save', booking.code)
    db.commit()
    return guest.id
