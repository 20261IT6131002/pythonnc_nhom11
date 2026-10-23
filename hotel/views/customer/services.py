from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class CustomerServicesMixin:
    def show_services(self):
        self._clear()
        self._banner('DỊCH VỤ TIỆN ÍCH', 'Chăm sóc bạn trong từng chi tiết',
                     'Ẩm thực, giặt là và các tiện ích dành cho kỳ nghỉ GrandStay.')
        self._service_features()
        section = self._section()
        text(section, 'Dịch vụ đang cung cấp', 19, NAVY, WHITE,
             'bold').pack(anchor='w', pady=(0, 20))
        for service in self.c.public_services():
            line = tk.Frame(section, bg=WHITE, highlightbackground=EDGE,
                            highlightthickness=1, padx=18, pady=15)
            line.pack(fill='x', pady=5)
            text(line, service['name'], 12, NAVY, WHITE, 'bold').pack(side='left')
            text(line, service['price'], 12, GOLD, WHITE, 'bold').pack(side='right')
        self._footer()
