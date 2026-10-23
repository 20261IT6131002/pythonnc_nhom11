"""Thanh menu trái dùng chung cho trang quản trị và lễ tân."""
import tkinter as tk

from hotel.views.components.theme import (
    FONT, SIDEBAR, SIDEBAR_HOVER, WHITE, brand,
)


NAV_GROUPS = [
    ('TỔNG QUAN', [('dashboard', '◫   Dashboard')]),
    ('NGHIỆP VỤ', [('bookings', '▦   Đặt phòng'), ('rooms', '▤   Quản lý phòng'),
                  ('calendar', '▦   Lịch phòng'), ('types', '◇   Loại phòng & giá'),
                  ('customers', '♙   Khách hàng'), ('services', '✦   Dịch vụ'),
                  ('invoices', '▣   Hóa đơn & thanh toán')]),
    ('QUẢN TRỊ', [('reports', '◴   Báo cáo doanh thu'), ('users', '♧   Nhân viên & quyền'),
                 ('logs', '≡   Nhật ký thao tác')]),
    ('KHÁC', [('chat', '✦   Tư vấn tự động')]),
]


def build_sidebar(view, app, allowed_tabs):
    """Tạo sidebar như giao diện gốc; trả về dict tab -> nút bấm."""
    left = tk.Frame(view, bg=SIDEBAR, width=252)
    left.pack(side='left', fill='y')
    left.pack_propagate(False)
    logo = brand(left, on_dark=True)
    logo.pack(anchor='w', padx=20, pady=(22, 24))
    tk.Frame(left, bg='#3c5970', height=1).pack(fill='x', padx=16, pady=(0, 13))
    buttons = {}
    for heading, entries in NAV_GROUPS:
        entries = [(key, label) for key, label in entries if key in allowed_tabs]
        if not entries:
            continue
        tk.Label(left, text=heading, fg='#7e9db6', bg=SIDEBAR,
                 font=(FONT, 9, 'bold'), anchor='w').pack(fill='x', padx=25,
                                                         pady=(17, 7))
        for key, label in entries:
            button = tk.Button(left, text=label, font=(FONT, 10, 'bold'),
                               bg=SIDEBAR, fg='#c3d4e2', activebackground=SIDEBAR_HOVER,
                               activeforeground=WHITE, relief='flat', bd=0, anchor='w',
                               cursor='hand2', padx=19, pady=9,
                               command=lambda tab=key: view._on_nav(tab))
            button.pack(fill='x', padx=10, pady=1)
            buttons[key] = button
    tk.Button(left, text='↗   Trang khách hàng', command=app.show_guest,
              bg=SIDEBAR, fg='#c3d4e2', activebackground=SIDEBAR_HOVER,
              activeforeground=WHITE, relief='flat', bd=0, cursor='hand2',
              font=(FONT, 10, 'bold'), anchor='w', padx=19, pady=9).pack(
                  fill='x', padx=10, pady=(12, 0))
    return buttons
