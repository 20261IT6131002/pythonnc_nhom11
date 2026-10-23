from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class CustomersScreenMixin:
    def _edit_customer(self, edit):
        row = self._chosen() if edit else {}
        values = form_dialog(self, 'Sửa khách hàng' if edit else 'Thêm khách hàng',
            [('name', 'Họ tên', row.get('name', '')),
             ('phone', 'Điện thoại', row.get('phone', '')),
             ('email', 'Email', row.get('email', '')),
             ('document_no', 'CCCD / Hộ chiếu', row.get('document_no', ''))])
        if values is not None:
            self.c.save_customer(values, row.get('id'))
            self._done()

    def _customer_history(self):
        selected = self._chosen()
        rows = [r for r in self.c.table('bookings') if r['phone'] == selected['phone']]
        text = '\n'.join(f"{x['code']} | Phòng {x['room']} | {x['checkin']} - {x['checkout']} | {x['status']}"
                         for x in rows[:25]) or 'Khách chưa có đơn đặt phòng.'
        success(self, f"Lịch sử khách: {selected['name']}\n\n{text}")
