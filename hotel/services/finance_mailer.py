"""Gửi email tài chính (hóa đơn, đặt cọc, hoàn tiền, biên lai thanh toán) của GrandStay."""
from __future__ import annotations

from decimal import Decimal
from hotel.models.entities import Booking, BookingDeposit, Invoice, Payment, Refund
from hotel.services import mailer


def resolve_customer_email(booking: Booking, explicit_email: str | None = None) -> str:
    if explicit_email and explicit_email.strip():
        return explicit_email.strip()
    if booking.customer:
        if booking.customer.email and booking.customer.email.strip():
            return booking.customer.email.strip()
        if getattr(booking.customer, 'user', None) and booking.customer.user and booking.customer.user.email:
            return booking.customer.user.email.strip()
    return ''


def send_deposit_confirmation(booking: Booking, deposit: BookingDeposit,
                              pdf_bytes: bytes | None = None,
                              recipient_email: str | None = None) -> bool:
    email = resolve_customer_email(booking, recipient_email)
    if not email:
        return False
    subject = f"[GrandStay] Xác nhận đặt cọc phòng #{booking.code}"
    method_name = {'cash': 'Tiền mặt', 'bank_transfer': 'Chuyển khoản', 'card_manual': 'Thẻ tín dụng/ghi nợ'}.get(deposit.method, deposit.method)
    body = (
        f"Kính gửi Quý khách {booking.customer.full_name if booking.customer else ''},\n\n"
        f"Khách sạn GrandStay xin trân trọng thông báo đã ghi nhận khoản tiền đặt cọc cho đơn đặt phòng của Quý khách:\n"
        f"  - Mã đặt phòng: {booking.code}\n"
        f"  - Phòng: {booking.room.number} ({booking.room.room_type.name})\n"
        f"  - Thời gian: {booking.checkin_date:%d/%m/%Y} đến {booking.checkout_date:%d/%m/%Y}\n"
        f"  - Số tiền đặt cọc: {deposit.amount:,.0f} VND\n"
        f"  - Phương thức: {method_name}\n"
        f"  - Mã giao dịch / Ghi chú: {deposit.reference or 'Không có'}\n"
        f"  - Trạng thái đơn: {booking.status}\n\n"
        f"Khoản tiền đặt cọc này sẽ được cấn trừ trực tiếp vào hóa đơn tổng khi Quý khách làm thủ tục trả phòng.\n"
        f"Đính kèm email này là Phiếu thu tiền đặt cọc điện tử.\n\n"
        f"Trân trọng cảm ơn Quý khách,\n"
        f"Ban quản lý GrandStay Hotel & Resort"
    )
    filename = f"phieu_dat_coc_{booking.code}.pdf" if pdf_bytes else None
    mailer.send_email_with_attachment(email, subject, body, pdf_bytes, filename)
    return True


def send_invoice_notification(invoice: Invoice, pdf_bytes: bytes | None = None,
                              customer_snapshot=None,
                              recipient_email: str | None = None) -> bool:
    booking = invoice.booking
    email = resolve_customer_email(booking, recipient_email)
    if not email:
        return False
    customer_name = customer_snapshot.full_name if customer_snapshot else (booking.customer.full_name if booking.customer else '')
    subject = f"[GrandStay] Hóa đơn thanh toán #{booking.code}"
    paid_total = sum((p.amount for p in invoice.payments), Decimal('0'))
    deposit_total = sum((d.amount for d in booking.deposits if d.status == 'paid'), Decimal('0'))
    total_paid = paid_total + deposit_total
    due_amount = max(Decimal('0'), invoice.total_amount - total_paid)
    status_str = "ĐÃ THANH TOÁN ĐỦ" if due_amount == 0 else f"CÒN THIẾU {due_amount:,.0f} VND"

    body = (
        f"Kính gửi Quý khách {customer_name},\n\n"
        f"Khách sạn GrandStay xin gửi đến Quý khách thông tin hóa đơn thanh toán cho kỳ lưu trú vừa qua:\n"
        f"  - Mã đặt phòng: {booking.code}\n"
        f"  - Phòng: {booking.room.number}\n"
        f"  - Thời gian: {booking.checkin_date:%d/%m/%Y} đến {booking.checkout_date:%d/%m/%Y}\n"
        f"  - Tiền phòng: {invoice.room_amount:,.0f} VND\n"
        f"  - Tiền dịch vụ: {invoice.services_amount:,.0f} VND\n"
        f"  - Khuyến mãi: -{invoice.discount_amount:,.0f} VND\n"
        f"  - TỔNG CỘNG: {invoice.total_amount:,.0f} VND\n"
        f"  - Đã đặt cọc: {deposit_total:,.0f} VND\n"
        f"  - Đã thanh toán: {paid_total:,.0f} VND\n"
        f"  - Còn thiếu: {due_amount:,.0f} VND\n"
        f"  - Tình trạng: {status_str}\n\n"
        f"Chi tiết đầy đủ các mục chi tiêu được đính kèm trong tệp PDF dưới đây.\n\n"
        f"GrandStay rất hân hạnh được phục vụ Quý khách và mong sớm được đón tiếp Quý khách trong những kỳ nghỉ tiếp theo!\n\n"
        f"Trân trọng,\n"
        f"GrandStay Hotel & Resort"
    )
    filename = f"hoa_don_{booking.code}.pdf" if pdf_bytes else None
    mailer.send_email_with_attachment(email, subject, body, pdf_bytes, filename)
    return True


def send_refund_notification(booking: Booking, refund: Refund,
                             pdf_bytes: bytes | None = None,
                             recipient_email: str | None = None) -> bool:
    email = resolve_customer_email(booking, recipient_email)
    if not email:
        return False
    subject = f"[GrandStay] Thông báo hoàn tiền #{booking.code}"
    method_name = {'cash': 'Tiền mặt', 'bank_transfer': 'Chuyển khoản', 'card_manual': 'Thẻ'}.get(refund.method, refund.method)
    body = (
        f"Kính gửi Quý khách {booking.customer.full_name if booking.customer else ''},\n\n"
        f"Khách sạn GrandStay xin thông báo giao dịch hoàn tiền cho đơn đặt phòng #{booking.code} đã được xử lý:\n"
        f"  - Mã đặt phòng: {booking.code}\n"
        f"  - Số tiền hoàn trả: {refund.amount:,.0f} VND\n"
        f"  - Phương thức hoàn: {method_name}\n"
        f"  - Lý do: {refund.reason or 'Hoàn tiền theo chính sách hủy phòng'}\n"
        f"  - Ngày giờ xử lý: {refund.created_at.strftime('%d/%m/%Y %H:%M')}\n\n"
        f"Nếu hoàn qua tài khoản ngân hàng, thời gian nhận tiền có thể từ 1-3 ngày làm việc tùy thuộc vào ngân hàng thụ hưởng.\n"
        f"Đính kèm email này là Phiếu chi hoàn tiền điện tử của khách sạn.\n\n"
        f"Trân trọng cảm ơn sự thông cảm của Quý khách,\n"
        f"GrandStay Hotel & Resort"
    )
    filename = f"phieu_hoan_tien_{booking.code}.pdf" if pdf_bytes else None
    mailer.send_email_with_attachment(email, subject, body, pdf_bytes, filename)
    return True


def send_payment_receipt(invoice: Invoice, payment: Payment,
                         recipient_email: str | None = None) -> bool:
    booking = invoice.booking
    email = resolve_customer_email(booking, recipient_email)
    if not email:
        return False
    subject = f"[GrandStay] Biên nhận thanh toán #{booking.code}"
    method_name = {'cash': 'Tiền mặt', 'bank_transfer': 'Chuyển khoản', 'card_manual': 'Thẻ'}.get(payment.method, payment.method)
    body = (
        f"Kính gửi Quý khách {booking.customer.full_name if booking.customer else ''},\n\n"
        f"Khách sạn GrandStay đã ghi nhận khoản thanh toán của Quý khách:\n"
        f"  - Mã đơn: {booking.code}\n"
        f"  - Số tiền: {payment.amount:,.0f} VND\n"
        f"  - Hình thức: {method_name}\n"
        f"  - Mã tham chiếu: {payment.reference or 'Không có'}\n"
        f"  - Thời gian: {payment.created_at.strftime('%d/%m/%Y %H:%M')}\n\n"
        f"Trân trọng cảm ơn Quý khách,\n"
        f"GrandStay Hotel & Resort"
    )
    mailer.send_email_with_attachment(email, subject, body)
    return True
