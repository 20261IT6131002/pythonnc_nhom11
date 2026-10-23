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
        solid_button(header, 'Nhân viên đăng nhập', self.app.show_login,
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













