from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd


class BillingControllerMixin:
    def make_invoice(self, booking_id):
        with self._session() as db:
            actor = self._require_staff(db)
            return business.ensure_invoice(db, self._must(db, Booking, booking_id), actor).id

    def pay(self, invoice_id, amount, method, reference=''):
        with self._session() as db:
            actor = self._require_staff(db)
            business.record_payment(db, self._must(db, Invoice, invoice_id), amount, method, reference, actor)

    def export_invoice(self, invoice_id, path):
        with self._session() as db:
            self._require_staff(db)
            binary = pdf_service.invoice_pdf(self._must(db, Invoice, invoice_id))
        Path(path).write_bytes(binary)

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
