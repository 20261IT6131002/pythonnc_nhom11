from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class LoginView(tk.Frame):
    def __init__(self, parent, controller, app):
        super().__init__(parent, bg=WHITE)
        self.c, self.app = controller, app
        header = tk.Frame(self, bg=WHITE, height=86, highlightthickness=1,
                          highlightbackground=EDGE)
        header.pack(fill='x')
        header.pack_propagate(False)
        brand(header, tagline='HOTEL & RESORT').pack(side='left', padx=45, pady=20)
        tk.Button(header, text='← Về trang chủ', bg=WHITE, fg=NAVY,
                  font=(FONT, 10, 'bold'), bd=0, cursor='hand2',
                  command=app.show_guest).pack(side='right', padx=45)
        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill='both', expand=True)
        panel = tk.Frame(body, bg=WHITE, width=465, padx=32, pady=34,
                         highlightbackground=EDGE, highlightthickness=1)
        panel.place(relx=.5, rely=.45, anchor='center')
        panel.pack_propagate(False)
        panel.configure(height=480)
        text(panel, 'DÀNH CHO NHÂN VIÊN', 10, GOLD, WHITE, 'bold').pack(anchor='w', pady=(0, 12))
        text(panel, 'Đăng nhập hệ thống', 23, NAVY, WHITE, 'bold').pack(anchor='w')
        text(panel, 'Quản lý đặt phòng, khách hàng, hóa đơn và doanh thu.',
             10, MUTED, WHITE, wraplength=385, justify='left').pack(anchor='w', pady=(8, 28))
        text(panel, 'Tên đăng nhập', 10, INK, WHITE, 'bold').pack(anchor='w')
        self.username = ttk.Entry(panel, width=42)
        self.username.pack(fill='x', ipady=8, pady=(7, 17))
        text(panel, 'Mật khẩu', 10, INK, WHITE, 'bold').pack(anchor='w')
        self.password = ttk.Entry(panel, width=42, show='•')
        self.password.pack(fill='x', ipady=8, pady=(7, 25))
        solid_button(panel, 'Đăng nhập →', self._login).pack(fill='x')
        text(panel, 'Tài khoản Admin ban đầu tạo bằng scripts.create_admin',
             9, MUTED, WHITE, wraplength=385).pack(pady=(24, 0))
        self.password.bind('<Return>', lambda _: self._login())
        self.username.focus_set()

    def _login(self):
        try:
            self.c.login(self.username.get(), self.password.get())
            self.app.show_staff()
        except Exception as exc:
            error(self, exc)
