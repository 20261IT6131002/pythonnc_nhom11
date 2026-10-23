from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class StaffDashboardMixin:
    def _dashboard(self):
        s = self.c.dashboard()
        cards = tk.Frame(self.body, bg=BACKGROUND)
        cards.pack(fill='x', pady=(0, 22))
        metrics = [
            ('Phòng đang hoạt động', s['rooms'], 'Phòng trong hệ thống'),
            ('Khách hàng', s['customers'], 'Hồ sơ đã lưu'),
            ('Đơn đặt phòng', s['bookings'], 'Tất cả trạng thái'),
            ('Đang lưu trú', s['staying'], 'Đã nhận phòng'),
            ('Doanh thu đã thu hôm nay', s['revenue'], 'Các khoản thanh toán ghi nhận'),
        ]
        for index, (label, value, note) in enumerate(metrics):
            cell = tk.Frame(cards, bg=WHITE, highlightbackground=EDGE,
                            highlightthickness=1, padx=17, pady=14)
            cell.grid(row=index // 4, column=index % 4, sticky='nsew', padx=5, pady=5)
            text(cell, label, 9, MUTED, WHITE, 'bold').pack(anchor='w')
            text(cell, str(value), 21 if index < 4 else 17, NAVY, WHITE,
                 'bold').pack(anchor='w', pady=(9, 7))
            text(cell, note, 8, '#a1afbb', WHITE).pack(anchor='w')
        for index in range(4):
            cards.grid_columnconfigure(index, weight=1, uniform='stat')
        recent_panel = tk.Frame(self.body, bg=WHITE, highlightbackground=EDGE,
                                highlightthickness=1, padx=17, pady=17)
        recent_panel.pack(fill='both', expand=True)
        text(recent_panel, 'Đặt phòng gần đây', 15, NAVY, WHITE,
             'bold').pack(anchor='w', pady=(0, 10))
        recent = [{'code': c, 'customer': u, 'room': r, 'status': t}
                  for c, u, r, t in s['recent']]
        add_tree(recent_panel, [('code', 'Mã đặt', 180), ('customer', 'Khách', 210),
                             ('room', 'Phòng', 100), ('status', 'Trạng thái', 160)],
                 recent, height=11)
