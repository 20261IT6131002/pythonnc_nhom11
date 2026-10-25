"""Tkinter root; visual language follows original GrandStay HTML template."""
from __future__ import annotations

from hotel.views.auth.login_view import LoginView

import tkinter as tk
from tkinter import ttk

from hotel.views.components.theme import (BACKGROUND, EDGE, FONT, GOLD, INK, MUTED, NAVY,
                                WHITE, brand, solid_button, text)
from hotel.views.components.widget_helpers import error
from hotel.views.components.widget_helpers import form_dialog, success
from tkinter import messagebox


class GrandStayApp(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title('GrandStay Hotel | Nhóm 11 · Tkinter MVC + MySQL')
        self.geometry('1380x860')
        self.minsize(1080, 690)
        self.configure(bg=BACKGROUND)
        style = ttk.Style(self)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('.', font=(FONT, 10), background=WHITE, foreground=INK)
        style.configure('TFrame', background=WHITE)
        style.configure('TLabel', background=WHITE, foreground=INK)
        style.configure('Headline.TLabel', background=BACKGROUND,
                        font=(FONT, 25, 'bold'), foreground=NAVY)
        style.configure('Title.TLabel', background=BACKGROUND,
                        font=(FONT, 17, 'bold'), foreground=NAVY)
        style.configure('FormTitle.TLabel', font=(FONT, 17, 'bold'), foreground=NAVY)
        style.configure('Page.TFrame', background=BACKGROUND)
        style.configure('Page.TLabel', background=BACKGROUND, foreground=INK)
        style.configure('Card.TFrame', background=WHITE)
        style.configure('TButton', font=(FONT, 10, 'bold'), padding=(14, 10))
        style.configure('Accent.TButton', background=NAVY, foreground=WHITE, padding=(17, 10))
        style.map('Accent.TButton', background=[('active', '#27547a')],
                  foreground=[('active', WHITE)])
        style.configure('Treeview', background=WHITE, fieldbackground=WHITE,
                        foreground=INK, rowheight=35, font=(FONT, 10), borderwidth=0)
        style.configure('Treeview.Heading', background='#f5f7fa', foreground='#7c8b99',
                        font=(FONT, 9, 'bold'), padding=(10, 11))
        style.map('Treeview', background=[('selected', '#dcecf9')],
                  foreground=[('selected', NAVY)])
        self.host = tk.Frame(self, bg=WHITE)
        self.host.pack(fill='both', expand=True)
        # Trang chủ của ZIP gốc là trang khách hàng, không phải màn hình đăng nhập.
        self.show_guest()

    def _replace(self, view_type, **kwargs):
        for child in self.host.winfo_children():
            child.destroy()
        view_type(self.host, self.controller, self, **kwargs).pack(fill='both', expand=True)

    def show_login(self):
        self.controller.logout()
        self._replace(LoginView)

    def show_staff(self):
        user = self.controller.get_current_user()
        if user['role'] not in ('admin', 'receptionist'):
            raise PermissionError('Bạn không có quyền vào trang nhân viên.')
        from hotel.views.staff import StaffView
        self._replace(StaffView)

    def show_customer(self):
        user = self.controller.get_current_user()
        if user['role'] != 'customer':
            raise PermissionError('Trang tài khoản chỉ dành cho khách hàng.')
        from hotel.views.guest import GuestView
        self._replace(GuestView)

    def show_guest(self):
        self.controller.logout()
        from hotel.views.guest import GuestView
        self._replace(GuestView)

    def change_password(self):
        values = form_dialog(self, 'Đổi mật khẩu', [
            ('old', 'Mật khẩu hiện tại', '', None, True),
            ('new', 'Mật khẩu mới (tối thiểu 8 ký tự)', '', None, True),
            ('confirm', 'Nhập lại mật khẩu mới', '', None, True),
        ])
        if values is None:
            return
        try:
            self.controller.change_password(values['old'], values['new'], values['confirm'])
            success(self, 'Đổi mật khẩu thành công.')
        except Exception as exc:
            error(self, exc)

    def account_menu(self):
        """Personal security actions live inside an account menu, not the header."""
        try:
            user = self.controller.get_current_user()
            values = form_dialog(self, 'Tài khoản của tôi', [
                ('action', 'Thao tác', 'Đổi mật khẩu',
                 ['Đổi mật khẩu', 'Xem thông tin tài khoản']),
            ])
            if values is None:
                return
            if values['action'] == 'Đổi mật khẩu':
                self.change_password()
            else:
                success(self, f"Họ tên: {user['name']}\nVai trò: {user['role']}\n"
                              f"Email: {user.get('email') or 'Chưa có (tài khoản cũ)'}\n"
                              f"Số điện thoại: {user.get('phone') or 'Chưa có'}")
        except Exception as exc:
            error(self, exc)

    def link_email(self):
        values = form_dialog(self, 'Xác minh email tài khoản', [
            ('email', 'Địa chỉ email muốn liên kết', ''),
            ('password', 'Mật khẩu hiện tại', '', None, True),
        ])
        if values is None:
            return
        try:
            self.controller.request_link_email(values['password'], values['email'])
            success(self, 'Đã gửi mã OTP đến email. Mã có hiệu lực 10 phút.')
            code = form_dialog(self, 'Nhập OTP xác minh email', [
                ('otp', 'Mã OTP 6 chữ số', ''),
            ])
            if code is None:
                return
            self.controller.confirm_link_email(values['email'], code['otp'])
            success(self, 'Đã liên kết và xác minh email thành công.')
        except Exception as exc:
            error(self, exc)


