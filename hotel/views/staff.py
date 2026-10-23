"""Main Tkinter staff view. Widgets call Controller; there are no SQL statements here."""
from __future__ import annotations

from hotel.views.receptionist.dashboard import StaffDashboardMixin
from hotel.views.admin.dashboard import AdminReportsMixin
from hotel.views.screens.rooms import RoomsScreenMixin
from hotel.views.screens.customers import CustomersScreenMixin
from hotel.views.screens.services import ServicesScreenMixin
from hotel.views.screens.bookings import BookingsScreenMixin
from hotel.views.screens.billing import BillingScreenMixin
from hotel.views.screens.admin import AdminScreenMixin
from hotel.views.screens.chat import StaffChatScreenMixin
import tkinter as tk
from tkinter import ttk

from hotel.views.components.theme import (
    BACKGROUND, EDGE, FONT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, text,
)
from hotel.views.components.widget_helpers import add_tree, error, success
from hotel.views.components.sidebar import build_sidebar
from hotel.views.pages import PAGE_DESCRIPTIONS, TABLE_COLUMNS, TAB_NAMES


class StaffView(StaffDashboardMixin, AdminReportsMixin, RoomsScreenMixin,
                CustomersScreenMixin, ServicesScreenMixin, BookingsScreenMixin,
                BillingScreenMixin, AdminScreenMixin, StaffChatScreenMixin, tk.Frame):
    def __init__(self, parent, controller, app):
        super().__init__(parent, bg=BACKGROUND)
        self.c, self.app = controller, app
        self.admin = controller.user['role'] == 'admin'
        self.current_tab = 'dashboard'
        self.tabs = [name for name in TAB_NAMES if self.admin or name not in ('reports', 'users', 'logs')]
        self.nav_buttons = build_sidebar(self, app, self.tabs)

        main = tk.Frame(self, bg=BACKGROUND)
        main.pack(side='left', fill='both', expand=True)
        header = tk.Frame(main, bg=WHITE, height=70, highlightthickness=1,
                          highlightbackground=EDGE)
        header.pack(fill='x')
        header.pack_propagate(False)
        text(header, 'Hệ thống quản lý khách sạn', 12, NAVY, WHITE,
             'bold').pack(side='left', padx=32)
        tk.Button(header, text='Đăng xuất', command=app.show_login,
                  bg=WHITE, fg='#c45c60', bd=0, cursor='hand2',
                  font=(FONT, 10, 'bold')).pack(side='right', padx=(0, 32))
        user = controller.user
        text(header, f"{user['name']}  ({user['role']})", 10, INK, WHITE,
             'bold').pack(side='right', padx=16)
        self.body = ttk.Frame(main, padding=(32, 28), style='Page.TFrame')
        self.body.pack(fill='both', expand=True)
        self.tree = None
        self.rows = []
        self.render('dashboard')

    def _on_nav(self, tab):
        self.current_tab = tab
        self.render(tab)

    def render(self, tab=None):
        tab = tab or self.current_tab
        self.current_tab = tab
        for key, button in self.nav_buttons.items():
            button.configure(bg=SIDEBAR_HOVER if key == tab else SIDEBAR,
                             fg=WHITE if key == tab else '#c3d4e2')
        for child in self.body.winfo_children():
            child.destroy()
        self.tree, self.rows = None, []
        text(self.body, 'BẢNG ĐIỀU KHIỂN' if tab == 'dashboard' else TAB_NAMES[tab].upper(),
             9, '#a68255', BACKGROUND, 'bold').pack(anchor='w', pady=(1, 7))
        title = 'Chào mừng trở lại 👋' if tab == 'dashboard' else TAB_NAMES[tab]
        text(self.body, title, 23, NAVY, BACKGROUND, 'bold').pack(anchor='w')
        text(self.body, PAGE_DESCRIPTIONS[tab], 10, MUTED, BACKGROUND).pack(
            anchor='w', pady=(7, 24))
        try:
            if tab == 'dashboard':
                self._dashboard()
            elif tab == 'calendar':
                self._calendar()
            elif tab == 'reports':
                self._reports()
            elif tab == 'chat':
                self._chat()
            else:
                self._table_tab(tab)
        except Exception as exc:
            error(self, exc)

    def _button(self, bar, text, callback, primary=False):
        return ttk.Button(bar, text=text, command=lambda: self._safe(callback),
                          style='Accent.TButton' if primary else 'TButton').pack(side='left', padx=(0, 8))

    def _safe(self, fn):
        try:
            fn()
        except Exception as exc:
            error(self, exc)

    def _done(self, message='Đã lưu thay đổi.'):
        success(self, message)
        self.render()

    def _chosen(self):
        if not self.tree or not self.tree.selection():
            raise ValueError('Hãy chọn một dòng trong bảng.')
        chosen = self.tree.selection()[0]
        return next(row for row in self.rows if str(row['id']) == chosen)


    def _table_tab(self, tab):
        self.rows = self.c.table(tab)
        panel = tk.Frame(self.body, bg=WHITE, highlightbackground=EDGE,
                         highlightthickness=1, padx=16, pady=16)
        panel.pack(fill='both', expand=True)
        bar = ttk.Frame(panel)
        bar.pack(fill='x', pady=(0, 10))
        self._button(bar, 'Làm mới', lambda: self.render())
        if tab == 'types' and self.admin:
            self._button(bar, 'Thêm loại phòng', lambda: self._edit_type(False), True)
            self._button(bar, 'Sửa loại phòng', lambda: self._edit_type(True))
        elif tab == 'rooms' and self.admin:
            self._button(bar, 'Thêm phòng', lambda: self._edit_room(False), True)
            self._button(bar, 'Sửa phòng', lambda: self._edit_room(True))
            self._button(bar, 'Mở / ngừng phòng', lambda: self._toggle('room'))
        elif tab == 'customers':
            self._button(bar, 'Thêm khách', lambda: self._edit_customer(False), True)
            self._button(bar, 'Sửa hồ sơ', lambda: self._edit_customer(True))
            self._button(bar, 'Lịch sử khách', self._customer_history)
        elif tab == 'bookings':
            self._button(bar, 'Đặt phòng mới', self._book, True)
            self._button(bar, 'Chuyển trạng thái', self._status)
            self._button(bar, 'Thêm dịch vụ', self._usage)
            self._button(bar, 'Chốt hóa đơn', self._invoice)
        elif tab == 'services' and self.admin:
            self._button(bar, 'Thêm dịch vụ', lambda: self._edit_service(False), True)
            self._button(bar, 'Sửa / bật tắt', lambda: self._edit_service(True))
        elif tab == 'invoices':
            self._button(bar, 'Ghi nhận thanh toán', self._payment, True)
            self._button(bar, 'Xuất hóa đơn PDF', self._invoice_pdf)
        elif tab == 'users' and self.admin:
            self._button(bar, 'Thêm nhân viên', self._add_user, True)
            self._button(bar, 'Khóa / mở', lambda: self._toggle('user'))
        self.tree = add_tree(panel, TABLE_COLUMNS[tab], self.rows)

















