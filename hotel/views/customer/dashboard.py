"""Public GrandStay views recreated in native Tkinter from original web templates."""
from __future__ import annotations

from hotel.views.customer.home import CustomerHomeMixin
from hotel.views.customer.rooms import CustomerRoomsMixin
from hotel.views.customer.lookup import CustomerLookupMixin
from hotel.views.customer.services import CustomerServicesMixin
from hotel.views.customer.chat import CustomerChatMixin


import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT,
                                INK, MUTED, NAVY, WHITE, brand, hotel_art,
                                solid_button, text)
from hotel.views.components.widget_helpers import error, form_dialog, success


class GuestView(CustomerHomeMixin, CustomerRoomsMixin, CustomerLookupMixin, CustomerServicesMixin, CustomerChatMixin, tk.Frame):
    def __init__(self, parent, controller, app):
        super().__init__(parent, bg=WHITE)
        self.c, self.app = controller, app
        self.start = tk.StringVar(value=str(date.today() + timedelta(days=1)))
        self.end = tk.StringVar(value=str(date.today() + timedelta(days=3)))
        self.guests = tk.StringVar(value='2')
        self.type_name = tk.StringVar(value='Tất cả')
        self._make_header()
        main = tk.Frame(self, bg=WHITE)
        main.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(main, bg=WHITE, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(main, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.content = tk.Frame(self.canvas, bg=WHITE)
        self.window = self.canvas.create_window(0, 0, window=self.content, anchor='nw')
        self.content.bind('<Configure>', lambda _: self.canvas.configure(
            scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda ev: self.canvas.itemconfigure(self.window, width=ev.width))
        self.canvas.bind_all('<MouseWheel>', self._wheel)
        self.chat_button = tk.Button(self, text='✦  Tư vấn 24/7', command=self.ask,
            bg=NAVY, fg=WHITE, font=(FONT, 10, 'bold'), relief='flat', bd=0,
            activebackground='#27547a', activeforeground=WHITE,
            cursor='hand2', padx=18, pady=12)
        self.chat_button.place(relx=1, rely=1, x=-25, y=-27, anchor='se')
        self.show_home()

    def destroy(self):
        self.canvas.unbind_all('<MouseWheel>')
        super().destroy()

    def _wheel(self, event):
        if self.winfo_exists() and event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), 'units')

    def _make_header(self):
        header = tk.Frame(self, bg=WHITE, height=86, highlightbackground=EDGE,
                          highlightthickness=1)
        header.pack(fill='x')
        header.pack_propagate(False)
        brand(header, tagline='HOTEL & RESORT').pack(side='left', padx=(45, 0), pady=20)
        user = self.c.user
        if user and user['role'] == 'customer':
            solid_button(header, 'Đăng xuất', self.app.show_guest,
                         light=True).pack(side='right', padx=(8, 45), pady=16)
            tk.Button(header, text=f"Tài khoản: {user['name']}", command=self.show_account,
                      bg=WHITE, fg=NAVY, bd=0, cursor='hand2',
                      font=(FONT, 10, 'bold')).pack(side='right', padx=8)
        else:
            solid_button(header, 'Đăng nhập / Đăng ký', self.app.show_login,
                         light=True).pack(side='right', padx=(8, 45), pady=16)
        for label, func in reversed([
            ('Trang chủ', self.show_home), ('Phòng nghỉ', self.show_rooms),
            ('Tiện ích', self.show_services), ('Tra cứu đặt phòng', self.show_lookup),
        ]):
            tk.Button(header, text=label, bg=WHITE, fg='#536274', bd=0,
                      relief='flat', cursor='hand2', font=(FONT, 10, 'bold'),
                      activeforeground=GOLD, command=func).pack(side='right', padx=13)

    def _clear(self):
        for child in self.content.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)

    def _section(self, padding=38, bg=WHITE):
        section = tk.Frame(self.content, bg=bg, padx=padding, pady=28)
        section.pack(fill='x')
        return section

    def show_account(self):
        self._clear()
        try:
            user = self.c.get_current_user()
            if user['role'] != 'customer':
                raise PermissionError('Vui lòng đăng nhập bằng tài khoản khách hàng.')
        except Exception as exc:
            error(self, exc)
            self.app.show_login()
            return
        section = self._section()
        text(section, 'TÀI KHOẢN KHÁCH HÀNG', 10, GOLD, WHITE, 'bold').pack(anchor='w')
        text(section, f"Xin chào, {user['name']}", 24, NAVY, WHITE, 'bold').pack(anchor='w', pady=(10, 15))
        text(section, 'Bạn đã đăng nhập thành công. Tại đây bạn có thể quản lý '
             'mật khẩu và tiếp tục xem phòng hoặc dịch vụ GrandStay.',
             11, MUTED, WHITE, wraplength=650).pack(anchor='w', pady=(0, 20))
        status = (f"Email đã xác minh: {user['email']}" if user.get('email_verified')
                  else 'Chưa liên kết email bảo mật.')
        text(section, status, 10, NAVY, WHITE, 'bold').pack(anchor='w', pady=(0, 15))
        if user.get('phone'):
            text(section, f"SĐT liên hệ: {user['phone']} (chưa xác minh bằng SMS)",
                 10, NAVY, WHITE).pack(anchor='w', pady=(0, 12))
        else:
            text(section, 'Tài khoản cũ chưa có SĐT. Vui lòng bổ sung trước khi đặt phòng.',
                 10, MUTED, WHITE).pack(anchor='w', pady=(0, 8))
        solid_button(section, 'Cập nhật số điện thoại', self.update_phone, light=True).pack(
            anchor='w', pady=(0, 12))
        text(section, 'ĐẶT PHÒNG CỦA TÔI', 13, NAVY, WHITE, 'bold').pack(
            anchor='w', pady=(10, 8))
        try:
            bookings = self.c.customer_history()
            for row in bookings[:20]:
                text(section, f"{row['code']} · Phòng {row['room']} · "
                     f"{row['checkin']} → {row['checkout']} · {row['status']}",
                     10, INK, WHITE).pack(anchor='w', pady=4)
            if not bookings:
                text(section, 'Chưa có đặt phòng được liên kết với tài khoản.',
                     10, MUTED, WHITE).pack(anchor='w')
        except Exception as exc:
            error(self, exc)
        solid_button(section, 'Liên kết lịch sử đặt phòng tại quầy',
                     self.request_old_history, light=True).pack(anchor='w', pady=(12, 20))
        text(section, 'BẢO MẬT TÀI KHOẢN', 13, NAVY, WHITE, 'bold').pack(
            anchor='w', pady=(10, 8))
        text(section, 'Để bảo vệ tài khoản, bạn có thể đổi mật khẩu hiện tại '
             'bất cứ lúc nào. Nếu quên, dùng OTP trong trang đăng nhập.',
             10, MUTED, WHITE, wraplength=650).pack(anchor='w', pady=(0, 12))
        solid_button(section, 'Đổi mật khẩu', self.app.change_password).pack(
            anchor='w', pady=(0, 16))
        solid_button(section, 'Tìm phòng →', self.show_rooms, light=True).pack(anchor='w')

    def request_old_history(self):
        values = form_dialog(self, 'Đề nghị liên kết lịch sử tại quầy', [
            ('code', 'Mã đặt phòng cũ (BK-...)', ''),
            ('phone', 'SĐT đã dùng tại quầy', ''),
        ])
        if values is None:
            return
        try:
            self.c.request_customer_link(values['code'], values['phone'])
            success(self, 'Đã gửi yêu cầu. Admin cần xác minh danh tính trực tiếp '\
                          'trước khi duyệt. Không tự liên kết chỉ bằng SĐT và mã đơn.')
        except Exception as exc:
            error(self, exc)

    def update_phone(self):
        values = form_dialog(self, 'Cập nhật SĐT tài khoản khách', [
            ('phone', 'SĐT mới (10 số hoặc +84)', ''),
            ('password', 'Mật khẩu hiện tại', '', None, True),
        ])
        if values is None:
            return
        try:
            self.c.set_customer_phone(values['password'], values['phone'])
            success(self, 'Đã lưu SĐT liên hệ. Số này chưa xác minh bằng SMS.')
            self.show_account()
        except Exception as exc:
            error(self, exc)













