"""Admin-only hotel configuration UI (N1)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from hotel.views.components.widget_helpers import error, success


FIELDS = [
    ('hotel_name', 'Tên khách sạn'),
    ('hotel_address', 'Địa chỉ'),
    ('hotel_phone', 'Điện thoại'),
    ('checkin_time', 'Giờ nhận phòng (HH:MM)'),
    ('checkout_time', 'Giờ trả phòng (HH:MM)'),
]


class AdminSettingsMixin:
    def _settings(self):
        values = self.c.get_settings()
        panel = ttk.Frame(self.body, padding=20)
        panel.pack(fill='x')
        fields = {}
        for row, (key, label) in enumerate(FIELDS):
            ttk.Label(panel, text=label).grid(row=row, column=0, sticky='w', padx=(0, 20), pady=10)
            value = tk.StringVar(value=values.get(key, ''))
            ttk.Entry(panel, textvariable=value, width=65).grid(row=row, column=1, sticky='ew', pady=10)
            fields[key] = value
        panel.columnconfigure(1, weight=1)

        def save():
            self.c.save_settings({key: field.get() for key, field in fields.items()})
            success(self, 'Cấu hình khách sạn đã được lưu trong MySQL.')

        buttons = ttk.Frame(self.body)
        buttons.pack(fill='x', pady=(14, 0))
        self._button(buttons, 'Lưu cấu hình', save, True)
