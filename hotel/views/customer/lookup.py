from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class CustomerLookupMixin:
    def show_lookup(self):
        self._clear()
        self._banner('GRANDSTAY RESERVATION', 'Tra cứu đặt phòng',
                     'Nhập mã đơn và số điện thoại đã sử dụng khi đặt phòng.')
        section = self._section()
        card = tk.Frame(section, bg=WHITE, highlightbackground=EDGE,
                        highlightthickness=1, padx=28, pady=26)
        card.pack(anchor='center', fill='x', padx=170)
        text(card, 'Tra cứu đặt phòng của bạn', 17, NAVY, WHITE, 'bold').pack(anchor='w')
        text(card, 'Thông tin đặt phòng được bảo vệ bằng mã đơn và số điện thoại.',
             10, MUTED, WHITE).pack(anchor='w', pady=(6, 22))
        code_var, phone_var = tk.StringVar(), tk.StringVar()
        for label, var in [('Mã đặt phòng', code_var), ('Số điện thoại', phone_var)]:
            text(card, label, 10, INK, WHITE, 'bold').pack(anchor='w', pady=(10, 6))
            ttk.Entry(card, textvariable=var).pack(fill='x', ipady=7)
        result = tk.Frame(card, bg=WHITE)
        result.pack(fill='x', pady=(18, 0))

        def lookup():
            try:
                booking = self.c.lookup(code_var.get(), phone_var.get())
                for child in result.winfo_children():
                    child.destroy()
                lines = [f"Mã đơn: {booking['code']}", f"Khách: {booking['customer']}",
                         f"Phòng: {booking['room']}",
                         f"Nhận / Trả: {booking['checkin']} → {booking['checkout']}",
                         f"Trạng thái: {booking['status']}"]
                for line in lines:
                    text(result, line, 11, NAVY, WHITE).pack(anchor='w', pady=5)
            except Exception as exc:
                error(self, exc)

        solid_button(card, 'Tra cứu →', lookup).pack(anchor='w', pady=(20, 0))
        self._footer()
