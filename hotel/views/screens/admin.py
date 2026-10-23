from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class AdminScreenMixin:
    def _toggle(self, what):
        row = self._chosen()
        if what == 'room':
            self.c.toggle_room(row['id'])
        else:
            self.c.toggle_user(row['id'])
        self._done('Đã cập nhật trạng thái.')

    def _add_user(self):
        values = form_dialog(self, 'Thêm tài khoản nhân viên',
            [('username', 'Tên đăng nhập', ''), ('name', 'Họ tên', ''),
             ('role', 'Vai trò', 'receptionist', ['receptionist', 'admin']),
             ('password', 'Mật khẩu (tối thiểu 8 ký tự)', '', None, True)])
        if values is not None:
            self.c.add_user(values)
            self._done('Tài khoản nhân viên đã được tạo.')
