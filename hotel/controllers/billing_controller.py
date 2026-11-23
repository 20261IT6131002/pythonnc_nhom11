from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, BookingDeposit, Customer,
                                   HotelService, Invoice, Payment, Refund, Room,
                                   RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, finance, finance_mailer, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd
from hotel.models.customer_services import InvoiceCustomerSnapshot


class BillingControllerMixin:
    def make_invoice(self, booking_id):
        with self._session(read_committed=True) as db:
            actor = self._require_staff(db)
            return business.ensure_invoice(db, self._must(db, Booking, booking_id), actor).id

    def pay(self, invoice_id, amount, method, reference=''):
        with self._session() as db:
            actor = self._require_staff(db)
            invoice = self._must(db, Invoice, invoice_id)
            payment = business.record_payment(db, invoice, amount, method, reference, actor)
            # Tự động gửi biên nhận thanh toán nếu có email khách
            try:
                finance_mailer.send_payment_receipt(invoice, payment)
            except Exception:
                pass

    def export_invoice(self, invoice_id, path, code=None, phone=None):
        with self._session() as db:
            user = self.user
            invoice = self._must(db, Invoice, invoice_id)
            if user:
                if user.get('role') in ('admin', 'receptionist'):
                    pass
                elif invoice.booking and invoice.booking.customer and invoice.booking.customer.user_id == user.get('id'):
                    pass
                elif code and phone and invoice.booking and invoice.booking.code == str(code).strip().upper() and invoice.booking.customer.phone == str(phone).strip():
                    pass
                else:
                    raise PermissionError('Không có quyền xuất hóa đơn của khách hàng khác.')
            binary = pdf_service.invoice_pdf(invoice, db.get(InvoiceCustomerSnapshot, invoice.id))
        Path(path).write_bytes(binary)

    def send_invoice_email(self, invoice_id, recipient_email=None):
        """Gửi email hóa đơn kèm tệp PDF cho khách hàng."""
        with self._session() as db:
            self._require_staff(db)
            invoice = self._must(db, Invoice, invoice_id)
            binary = pdf_service.invoice_pdf(invoice, db.get(InvoiceCustomerSnapshot, invoice.id))
            snapshot = db.get(InvoiceCustomerSnapshot, invoice.id)
            sent = finance_mailer.send_invoice_notification(invoice, binary, snapshot, recipient_email)
            if not sent:
                raise ValueError('Không tìm thấy địa chỉ email hợp lệ của khách hàng để gửi hóa đơn.')

    def record_deposit(self, booking_id, amount, method, reference='', notes='', send_email=True):
        """Ghi nhận tiền đặt cọc cho đơn đặt phòng."""
        with self._session() as db:
            actor = self._require_staff(db)
            booking = self._must(db, Booking, booking_id)
            deposit = finance.record_deposit(db, booking, amount, method, reference, actor, notes)
            deposit_id = deposit.id
            if send_email:
                try:
                    pdf_bytes = pdf_service.deposit_receipt_pdf(deposit, booking)
                    finance_mailer.send_deposit_confirmation(booking, deposit, pdf_bytes)
                except Exception:
                    pass
            return deposit_id

    def export_deposit_receipt(self, deposit_id, path):
        """Xuất phiếu thu tiền đặt cọc ra tệp PDF."""
        with self._session() as db:
            self._require_staff(db)
            deposit = self._must(db, BookingDeposit, deposit_id)
            binary = pdf_service.deposit_receipt_pdf(deposit, deposit.booking)
        Path(path).write_bytes(binary)

    def send_deposit_email(self, deposit_id, recipient_email=None):
        """Gửi email phiếu thu tiền đặt cọc kèm file PDF."""
        with self._session() as db:
            self._require_staff(db)
            deposit = self._must(db, BookingDeposit, deposit_id)
            binary = pdf_service.deposit_receipt_pdf(deposit, deposit.booking)
            sent = finance_mailer.send_deposit_confirmation(deposit.booking, deposit, binary, recipient_email)
            if not sent:
                raise ValueError('Đơn đặt phòng chưa có thông tin email để gửi phiếu cọc.')

    def suggest_refund(self, booking_id):
        """Gợi ý số tiền hoàn hủy theo chính sách khách sạn."""
        with self._session() as db:
            self._require_staff(db)
            booking = self._must(db, Booking, booking_id)
            return finance.suggest_cancellation_refund(booking)

    def record_refund(self, booking_id, amount, method, reason='', send_email=True):
        """Ghi nhận hoàn tiền (hoàn cọc, hủy phòng, trả thừa)."""
        with self._session() as db:
            actor = self._require_staff(db)
            booking = self._must(db, Booking, booking_id)
            refund = finance.record_refund(db, booking, amount, method, reason, actor)
            refund_id = refund.id
            if send_email:
                try:
                    pdf_bytes = pdf_service.refund_receipt_pdf(refund, booking)
                    finance_mailer.send_refund_notification(booking, refund, pdf_bytes)
                except Exception:
                    pass
            return refund_id

    def export_refund_receipt(self, refund_id, path):
        """Xuất phiếu chi hoàn tiền ra tệp PDF."""
        with self._session() as db:
            self._require_staff(db)
            refund = self._must(db, Refund, refund_id)
            binary = pdf_service.refund_receipt_pdf(refund, refund.booking)
        Path(path).write_bytes(binary)

    def send_refund_email(self, refund_id, recipient_email=None):
        """Gửi email thông báo hoàn tiền kèm tệp PDF."""
        with self._session() as db:
            self._require_staff(db)
            refund = self._must(db, Refund, refund_id)
            binary = pdf_service.refund_receipt_pdf(refund, refund.booking)
            sent = finance_mailer.send_refund_notification(refund.booking, refund, binary, recipient_email)
            if not sent:
                raise ValueError('Đơn đặt phòng chưa có thông tin email để gửi phiếu hoàn tiền.')

    def get_invoice_details(self, invoice_id):
        """Xem chi tiết cơ cấu một hóa đơn: tiền phòng, dịch vụ, cọc, các đợt thanh toán, hoàn tiền."""
        with self._session() as db:
            self._require_staff(db)
            inv = self._must(db, Invoice, invoice_id)
            b = inv.booking
            deposits = [{'id': d.id, 'amount': vnd(d.amount), 'method': d.method,
                         'reference': d.reference, 'status': d.status,
                         'date': d.created_at.strftime('%Y-%m-%d %H:%M')}
                        for d in (b.deposits if b else [])]
            payments = [{'id': p.id, 'amount': vnd(p.amount), 'method': p.method,
                         'reference': p.reference,
                         'date': p.created_at.strftime('%Y-%m-%d %H:%M')}
                        for p in inv.payments]
            refunds = [{'id': r.id, 'amount': vnd(r.amount), 'method': r.method,
                        'reason': r.reason,
                        'date': r.created_at.strftime('%Y-%m-%d %H:%M')}
                       for r in (b.refunds if b else [])]
            deposit_total = sum((d.amount for d in b.deposits if d.status in ('paid', 'applied')), Decimal('0')) if b else Decimal('0')
            payment_total = sum((p.amount for p in inv.payments), Decimal('0'))
            refund_total = sum((r.amount for r in b.refunds if r.status == 'completed'), Decimal('0')) if b else Decimal('0')
            net_paid = max(Decimal('0'), deposit_total + payment_total - refund_total)
            due = business.invoice_due(inv)

            return {
                'id': inv.id,
                'code': b.code if b else '',
                'customer': b.customer.full_name if b and b.customer else '',
                'room': b.room.number if b and b.room else '',
                'room_amount': vnd(inv.room_amount),
                'services_amount': vnd(inv.services_amount),
                'discount_amount': vnd(inv.discount_amount),
                'total_amount': vnd(inv.total_amount),
                'deposit_total': vnd(deposit_total),
                'payment_total': vnd(payment_total),
                'refund_total': vnd(refund_total),
                'net_paid': vnd(net_paid),
                'due': vnd(due),
                'status': 'Đã thanh toán đủ' if due == 0 else f'Còn thiếu {vnd(due)}',
                'deposits': deposits,
                'payments': payments,
                'refunds': refunds,
            }

    def report(self, start, end):
        d1, d2 = date.fromisoformat(start), date.fromisoformat(end)
        with self._session() as db:
            self._require_staff(db, admin=True)
            payments, total = business.revenue_summary(db, d1, d2)
            return {'total': vnd(total), 'count': len(payments), 'rows': [
                {'id': p.id, 'date': str(p.created_at.date()), 'code': p.invoice.booking.code,
                 'amount': vnd(p.amount)} for p in payments]}

    def export_report(self, start, end, path):
        d1, d2 = date.fromisoformat(start), date.fromisoformat(end)
        with self._session() as db:
            self._require_staff(db, admin=True)
            payments, total = business.revenue_summary(db, d1, d2)
            binary = pdf_service.report_pdf(d1, d2, payments, total)
        Path(path).write_bytes(binary)

    def comprehensive_financial_report(self, start, end):
        """Báo cáo tài chính toàn diện có cơ cấu và danh sách chi tiết."""
        d1, d2 = date.fromisoformat(start), date.fromisoformat(end)
        with self._session() as db:
            self._require_staff(db, admin=True)
            rep = finance.comprehensive_financial_report(db, d1, d2)
            # Định dạng VND cho giao diện
            return {
                'date_from': str(d1),
                'date_to': str(d2),
                'payments_count': rep['payments_count'],
                'payments_total': vnd(rep['payments_total']),
                'deposits_count': rep['deposits_count'],
                'deposits_total': vnd(rep['deposits_total']),
                'refunds_count': rep['refunds_count'],
                'refunds_total': vnd(rep['refunds_total']),
                'gross_revenue': vnd(rep['gross_revenue']),
                'net_revenue': vnd(rep['net_revenue']),
                'invoices_count': rep['invoices_count'],
                'total_invoice_amount': vnd(rep['total_invoice_amount']),
                'total_due': vnd(rep['total_due']),
                'methods': [
                    {'name': m['name'],
                     'payment': vnd(m['payment']),
                     'deposit': vnd(m['deposit']),
                     'refund': vnd(m['refund']),
                     'net': vnd(m['net'])}
                    for m in rep['methods'].values()
                ],
                'room_types': [
                    {'name': name, 'count': info['count'],
                     'room_amount': vnd(info['room_amount']),
                     'services_amount': vnd(info['services_amount']),
                     'total': vnd(info['total'])}
                    for name, info in rep['room_types'].items()
                ],
                'transactions': [
                    {'id': t['id'], 'type': t['type'], 'code': t['code'],
                     'customer': t['customer'], 'amount': vnd(t['amount']),
                     'method': t['method'], 'date': t['date'], 'reference': t['reference']}
                    for t in rep['transactions']
                ],
            }

    def export_comprehensive_financial_report(self, start, end, path):
        """Xuất PDF báo cáo tài chính toàn diện."""
        d1, d2 = date.fromisoformat(start), date.fromisoformat(end)
        with self._session() as db:
            self._require_staff(db, admin=True)
            rep = finance.comprehensive_financial_report(db, d1, d2)
            binary = pdf_service.comprehensive_report_pdf(d1, d2, rep)
        Path(path).write_bytes(binary)

