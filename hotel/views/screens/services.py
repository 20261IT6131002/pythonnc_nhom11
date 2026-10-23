from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class ServicesScreenMixin:
    def _edit_service(self, edit):
        row = self._chosen() if edit else {}
        values = form_dialog(self, 'Sửa dịch vụ' if edit else 'Thêm dịch vụ',
            [('name', 'Tên dịch vụ', row.get('name', '')),
             ('price', 'Đơn giá (VND)', row.get('price', '50000')),
             ('active', 'Đang cung cấp', 'Có' if row.get('active', True) else 'Không', ['Có', 'Không'])])
        if values is not None:
            values['active'] = values['active'] == 'Có'
            self.c.save_service(values, row.get('id'))
            self._done()
