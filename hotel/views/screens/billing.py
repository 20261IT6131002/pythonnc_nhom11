from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class BillingScreenMixin:
    def _invoice(self):
        row = self._chosen()
        invoice_id = self.c.make_invoice(row['id'])
        self._done(f'Đã chốt hóa đơn số {invoice_id}. Sang mục Hóa đơn để thu tiền.')

    def _payment(self):
        row = self._chosen()
        values = form_dialog(self, 'Ghi nhận tiền đã xác minh',
            [('amount', 'Số tiền (VND)', ''),
             ('method', 'Hình thức', 'cash', ['cash', 'bank_transfer', 'card_manual']),
             ('reference', 'Mã tham chiếu / Ghi chú', '')])
        if values is not None:
            self.c.pay(row['id'], values['amount'], values['method'], values['reference'])
            self._done('Đã ghi nhận thanh toán. Đây không phải tích hợp cổng ngân hàng.')

    def _invoice_pdf(self):
        row = self._chosen()
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.pdf',
            initialfile=f"hoa_don_{row['code']}.pdf", filetypes=[('PDF', '*.pdf')])
        if path:
            self.c.export_invoice(row['id'], path)
            success(self, 'Đã lưu hóa đơn PDF tại:\n' + path)
