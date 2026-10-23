"""Tkinter root; visual language follows original GrandStay HTML template."""
from __future__ import annotations

from hotel.views.auth.login_view import LoginView

import tkinter as tk
from tkinter import ttk

from hotel.views.components.theme import (BACKGROUND, EDGE, FONT, GOLD, INK, MUTED, NAVY,
                                WHITE, brand, solid_button, text)
from hotel.views.components.widget_helpers import error


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

    def _replace(self, view_type):
        for child in self.host.winfo_children():
            child.destroy()
        view_type(self.host, self.controller, self).pack(fill='both', expand=True)

    def show_login(self):
        self.controller.logout()
        self._replace(LoginView)

    def show_staff(self):
        from hotel.views.staff import StaffView
        self._replace(StaffView)

    def show_guest(self):
        self.controller.logout()
        from hotel.views.guest import GuestView
        self._replace(GuestView)


