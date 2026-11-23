"""Nghiệp vụ tài chính nâng cao: Đặt cọc, Hoàn tiền, Báo cáo tài chính toàn diện."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hotel.models.entities import (AuditLog, Booking, BookingDeposit, Customer,
                                   HotelService, Invoice, Payment, Refund, Room,
                                   RoomType, ServiceUsage, User)
from hotel.models.common import utc_now
from hotel.services.business import log_event, money


def booking_deposits_total(booking: Booking) -> Decimal:
    """Tổng tiền cọc còn hiệu lực (chưa bị hoàn trả)."""
    if not booking or not booking.deposits:
        return Decimal('0')
    return sum((d.amount for d in booking.deposits if d.status in ('paid', 'applied')), Decimal('0'))


def booking_payments_total(booking: Booking) -> Decimal:
    """Tổng tiền đã thanh toán cho hóa đơn của đơn đặt phòng."""
    if not booking or not booking.invoice or not booking.invoice.payments:
        return Decimal('0')
    return sum((p.amount for p in booking.invoice.payments), Decimal('0'))


def booking_refunds_total(booking: Booking) -> Decimal:
    """Tổng tiền đã hoàn lại cho khách hàng của đơn đặt phòng."""
    if not booking or not booking.refunds:
        return Decimal('0')
    return sum((r.amount for r in booking.refunds if r.status == 'completed'), Decimal('0'))


def booking_total_collected(booking: Booking) -> Decimal:
    """Tổng số tiền thực tế khách đã đóng (cọc + thanh toán)."""
    return booking_deposits_total(booking) + booking_payments_total(booking)


def booking_net_paid(booking: Booking) -> Decimal:
    """Tổng tiền khách đã thanh toán trừ đi số tiền đã hoàn lại."""
    return max(Decimal('0'), booking_total_collected(booking) - booking_refunds_total(booking))


def calculate_suggested_deposit(booking: Booking, percentage: int = 30) -> Decimal:
    """Tính số tiền đặt cọc gợi ý (mặc định 30% tiền phòng dự kiến hoặc tối thiểu 1 đêm)."""
    nights = max(1, (booking.checkout_date - booking.checkin_date).days)
    room_total = booking.nightly_price * nights
    # 30% tổng tiền phòng, làm tròn đến hàng nghìn
    suggested = (room_total * Decimal(percentage) / Decimal(100)).quantize(Decimal('1000'))
    one_night = booking.nightly_price.quantize(Decimal('1000'))
    return min(room_total, max(one_night, suggested))


def record_deposit(db: Session, booking: Booking, amount: Decimal | str | float,
                   method: str, reference: str = '', actor_id: int | None = None,
                   notes: str = '') -> BookingDeposit:
    """Ghi nhận tiền đặt cọc cho đơn đặt phòng."""
    booking = db.scalar(select(Booking).where(Booking.id == booking.id).with_for_update())
    if not booking:
        raise ValueError('Không tìm thấy đơn đặt phòng.')
    if booking.status in ('checked_out', 'cancelled'):
        raise ValueError('Không thể nhận cọc cho đơn đã trả phòng hoặc đã hủy.')

    amount = money(amount)
    if amount <= 0:
        raise ValueError('Số tiền đặt cọc phải lớn hơn 0.')

    nights = max(1, (booking.checkout_date - booking.checkin_date).days)
    expected_room_amount = booking.nightly_price * nights
    already_deposited = booking_deposits_total(booking)

    if already_deposited + amount > expected_room_amount * Decimal('1.5'):
        raise ValueError(f'Tổng tiền cọc ({already_deposited + amount:,.0f} VND) không được vượt quá 150% tiền phòng dự kiến.')

    if method not in {'cash', 'bank_transfer', 'card_manual'}:
        raise ValueError('Phương thức thanh toán cọc không hợp lệ.')

    deposit = BookingDeposit(
        booking_id=booking.id,
        amount=amount,
        method=method,
        reference=str(reference)[:100],
        status='paid',
        recorded_by=actor_id,
        notes=str(notes)[:500],
    )
    db.add(deposit)

    # Nếu đơn đang ở trạng thái pending (chờ xác nhận), nhận cọc sẽ tự động chuyển sang confirmed
    if booking.status == 'pending':
        booking.status = 'confirmed'
        log_event(db, actor_id, 'booking.status', f'{booking.code}: confirmed (sau khi nhận cọc)')

    log_event(db, actor_id, 'deposit.record', f'Đơn {booking.code} - Cọc {amount:,.0f} VND ({method})')
    db.commit()
    db.refresh(deposit)
    return deposit


def suggest_cancellation_refund(booking: Booking) -> dict:
    """Gợi ý số tiền hoàn hủy theo chính sách của khách sạn:
    - Hủy trước ngày nhận phòng >= 3 ngày: Hoàn 100% số tiền đã đóng.
    - Hủy trước ngày nhận phòng 1-2 ngày: Hoàn 50% số tiền đã đóng (phí phạt 50%).
    - Hủy trong ngày nhận hoặc sau đó: Không hoàn cọc (phí phạt 100%).
    """
    total_collected = booking_total_collected(booking)
    total_refunded = booking_refunds_total(booking)
    refundable_limit = max(Decimal('0'), total_collected - total_refunded)

    if refundable_limit <= 0:
        return {
            'suggested_amount': Decimal('0'),
            'refundable_limit': Decimal('0'),
            'policy': 'Chưa có khoản tiền nào để hoàn lại.',
            'days_ahead': 0
        }

    days_ahead = (booking.checkin_date - date.today()).days
    if days_ahead >= 3:
        suggested = refundable_limit
        policy = f'Hủy trước ngày nhận phòng {days_ahead} ngày (≥ 3 ngày): Hoàn 100% tiền đã thu ({suggested:,.0f} VND).'
    elif 1 <= days_ahead < 3:
        suggested = (refundable_limit * Decimal('0.5')).quantize(Decimal('1000'))
        policy = f'Hủy trước ngày nhận phòng {days_ahead} ngày (1-2 ngày): Hoàn 50% ({suggested:,.0f} VND), phí phạt hủy 50%.'
    else:
        suggested = Decimal('0')
        policy = 'Hủy trong ngày nhận phòng hoặc quá hạn: Phí phạt 100% (không hoàn tiền theo chính sách).'

    return {
        'suggested_amount': suggested,
        'refundable_limit': refundable_limit,
        'policy': policy,
        'days_ahead': days_ahead
    }


def record_refund(db: Session, booking: Booking, amount: Decimal | str | float,
                  method: str, reason: str = '', actor_id: int | None = None,
                  deposit_id: int | None = None, invoice_id: int | None = None) -> Refund:
    """Ghi nhận giao dịch hoàn tiền cho khách hàng."""
    booking = db.scalar(select(Booking).where(Booking.id == booking.id).with_for_update())
    if not booking:
        raise ValueError('Không tìm thấy đơn đặt phòng.')

    amount = money(amount)
    if amount <= 0:
        raise ValueError('Số tiền hoàn lại phải lớn hơn 0.')

    total_collected = booking_total_collected(booking)
    total_refunded = booking_refunds_total(booking)
    refundable_limit = max(Decimal('0'), total_collected - total_refunded)

    if amount > refundable_limit:
        raise ValueError(f'Số tiền hoàn ({amount:,.0f} VND) vượt quá số tiền có thể hoàn ({refundable_limit:,.0f} VND).')

    if method not in {'cash', 'bank_transfer', 'card_manual'}:
        raise ValueError('Phương thức hoàn tiền không hợp lệ.')

    # Tìm deposit liên quan nếu có
    if not deposit_id and booking.deposits:
        active_deposits = [d for d in booking.deposits if d.status == 'paid']
        if active_deposits:
            deposit_id = active_deposits[0].id

    # Tìm invoice liên quan nếu có
    if not invoice_id and booking.invoice:
        invoice_id = booking.invoice.id

    refund = Refund(
        booking_id=booking.id,
        invoice_id=invoice_id,
        deposit_id=deposit_id,
        amount=amount,
        method=method,
        reason=str(reason)[:255] or 'Hoàn tiền cho khách hàng',
        status='completed',
        recorded_by=actor_id,
    )
    db.add(refund)

    # Cập nhật trạng thái tiền cọc nếu hoàn hết cọc
    if deposit_id:
        dep = db.get(BookingDeposit, deposit_id)
        if dep:
            total_dep_refunded = sum((r.amount for r in dep.refunds), Decimal('0')) + amount
            if total_dep_refunded >= dep.amount:
                dep.status = 'refunded'

    log_event(db, actor_id, 'refund.record', f'Đơn {booking.code} - Hoàn {amount:,.0f} VND ({method}): {reason}')
    db.commit()
    db.refresh(refund)
    return refund


def comprehensive_financial_report(db: Session, date_from: date, date_to: date) -> dict:
    """Thống kê & Báo cáo tài chính toàn diện cho Quản lý / Admin:
    - Doanh thu hóa đơn (Payments)
    - Tiền cọc thu được (Deposits)
    - Tiền hoàn lại cho khách (Refunds)
    - Doanh thu thuần (Net Revenue)
    - Công nợ chưa thanh toán (Due)
    - Cơ cấu theo phương thức thanh toán
    - Cơ cấu theo loại phòng & dịch vụ
    - Danh sách giao dịch chi tiết
    """
    if date_from > date_to:
        raise ValueError('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')

    d1_iso = date_from.isoformat()
    d2_iso = date_to.isoformat()

    # 1. Các khoản thanh toán hóa đơn
    payments = db.scalars(
        select(Payment)
        .where(func.date(Payment.created_at) >= d1_iso,
               func.date(Payment.created_at) <= d2_iso)
        .order_by(Payment.created_at.desc())
    ).all()

    # 2. Các khoản đặt cọc
    deposits = db.scalars(
        select(BookingDeposit)
        .where(func.date(BookingDeposit.created_at) >= d1_iso,
               func.date(BookingDeposit.created_at) <= d2_iso)
        .order_by(BookingDeposit.created_at.desc())
    ).all()

    # 3. Các khoản hoàn tiền
    refunds = db.scalars(
        select(Refund)
        .where(func.date(Refund.created_at) >= d1_iso,
               func.date(Refund.created_at) <= d2_iso)
        .order_by(Refund.created_at.desc())
    ).all()

    # 4. Các hóa đơn trong kỳ để tính công nợ và cơ cấu
    invoices = db.scalars(
        select(Invoice)
        .where(func.date(Invoice.created_at) >= d1_iso,
               func.date(Invoice.created_at) <= d2_iso)
    ).all()

    # Tổng tiền
    payments_total = sum((p.amount for p in payments), Decimal('0'))
    deposits_total = sum((d.amount for d in deposits if d.status in ('paid', 'applied')), Decimal('0'))
    refunds_total = sum((r.amount for r in refunds if r.status == 'completed'), Decimal('0'))
    gross_revenue = payments_total + deposits_total
    net_revenue = gross_revenue - refunds_total

    # Tính công nợ hóa đơn trong kỳ
    total_invoice_amount = sum((inv.total_amount for inv in invoices), Decimal('0'))
    from hotel.services.business import invoice_due
    total_due = sum((invoice_due(inv) for inv in invoices), Decimal('0'))

    # Cơ cấu phương thức thanh toán
    method_labels = {'cash': 'Tiền mặt', 'bank_transfer': 'Chuyển khoản', 'card_manual': 'Thẻ tín dụng / ghi nợ'}
    methods_data = {k: {'name': label, 'payment': Decimal('0'), 'deposit': Decimal('0'), 'refund': Decimal('0'), 'net': Decimal('0')}
                    for k, label in method_labels.items()}

    for p in payments:
        if p.method in methods_data:
            methods_data[p.method]['payment'] += p.amount
    for d in deposits:
        if d.method in methods_data and d.status in ('paid', 'applied'):
            methods_data[d.method]['deposit'] += d.amount
    for r in refunds:
        if r.method in methods_data and r.status == 'completed':
            methods_data[r.method]['refund'] += r.amount

    for m in methods_data.values():
        m['net'] = (m['payment'] + m['deposit']) - m['refund']

    # Cơ cấu doanh thu theo Loại phòng
    room_type_revenue: dict[str, dict] = {}
    for inv in invoices:
        rt_name = inv.booking.room.room_type.name if inv.booking and inv.booking.room and inv.booking.room.room_type else 'Khác'
        if rt_name not in room_type_revenue:
            room_type_revenue[rt_name] = {'count': 0, 'room_amount': Decimal('0'), 'services_amount': Decimal('0'), 'total': Decimal('0')}
        room_type_revenue[rt_name]['count'] += 1
        room_type_revenue[rt_name]['room_amount'] += inv.room_amount
        room_type_revenue[rt_name]['services_amount'] += inv.services_amount
        room_type_revenue[rt_name]['total'] += inv.total_amount

    # Danh sách giao dịch hợp nhất
    transactions = []
    for p in payments:
        transactions.append({
            'id': f"PAY-{p.id}",
            'type': 'Thanh toán',
            'code': p.invoice.booking.code if p.invoice and p.invoice.booking else '-',
            'customer': p.invoice.booking.customer.full_name if p.invoice and p.invoice.booking and p.invoice.booking.customer else '-',
            'amount': p.amount,
            'method': method_labels.get(p.method, p.method),
            'date': p.created_at.strftime('%Y-%m-%d %H:%M'),
            'reference': p.reference or '',
        })
    for d in deposits:
        transactions.append({
            'id': f"DEP-{d.id}",
            'type': 'Đặt cọc',
            'code': d.booking.code if d.booking else '-',
            'customer': d.booking.customer.full_name if d.booking and d.booking.customer else '-',
            'amount': d.amount,
            'method': method_labels.get(d.method, d.method),
            'date': d.created_at.strftime('%Y-%m-%d %H:%M'),
            'reference': f"Cọc ({d.status}) - {d.reference}",
        })
    for r in refunds:
        transactions.append({
            'id': f"REF-{r.id}",
            'type': 'Hoàn tiền',
            'code': r.booking.code if r.booking else '-',
            'customer': r.booking.customer.full_name if r.booking and r.booking.customer else '-',
            'amount': -r.amount,
            'method': method_labels.get(r.method, r.method),
            'date': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'reference': f"Hoàn ({r.reason})",
        })

    transactions.sort(key=lambda x: x['date'], reverse=True)

    return {
        'date_from': date_from,
        'date_to': date_to,
        'payments_count': len(payments),
        'payments_total': payments_total,
        'deposits_count': len(deposits),
        'deposits_total': deposits_total,
        'refunds_count': len(refunds),
        'refunds_total': refunds_total,
        'gross_revenue': gross_revenue,
        'net_revenue': net_revenue,
        'invoices_count': len(invoices),
        'total_invoice_amount': total_invoice_amount,
        'total_due': total_due,
        'methods': methods_data,
        'room_types': room_type_revenue,
        'transactions': transactions,
    }
