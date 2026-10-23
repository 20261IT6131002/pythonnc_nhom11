from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class BookingsScreenMixin:
    def _book(self):
        today = date.today()
        choices = [label for _, label in self.c.choices('rooms')]
        values = form_dialog(self, 'Đặt phòng tại quầy lễ tân',
            [('name', 'Họ tên khách', ''), ('phone', 'Điện thoại', ''),
             ('email', 'Email', ''), ('room_id', 'Phòng', choices[0] if choices else '', choices),
             ('checkin', 'Ngày nhận (YYYY-MM-DD)', str(today + timedelta(days=1))),
             ('checkout', 'Ngày trả (YYYY-MM-DD)', str(today + timedelta(days=3))),
             ('guests', 'Số khách', '2'), ('notes', 'Ghi chú', '')])
        if values is not None:
            values['room_id'] = choice_id(values['room_id'])
            code = self.c.book(values)
            self._done(f'Đặt phòng thành công: {code}\nTrạng thái: confirmed.\n'
                       'Hệ thống đã kiểm tra phòng trống trong toàn bộ khoảng ngày.')

    def _status(self):
        row = self._chosen()
        statuses = ['confirmed', 'checked_in', 'checked_out', 'cancelled']
        values = form_dialog(self, 'Chuyển trạng thái đặt phòng',
            [('status', f"Đơn {row['code']} đang {row['status']}", statuses[0], statuses)])
        if values is not None:
            self.c.set_booking_status(row['id'], values['status'])
            self._done(f"Đơn {row['code']} đã chuyển sang {values['status']}.")

    def _usage(self):
        row = self._chosen()
        choices = [label for _, label in self.c.choices('services')]
        values = form_dialog(self, 'Ghi nhận dịch vụ phát sinh',
            [('service', f"Đơn {row['code']} / Dịch vụ", choices[0] if choices else '', choices),
             ('quantity', 'Số lượng', '1')])
        if values is not None:
            self.c.add_usage(row['id'], choice_id(values['service']), values['quantity'])
            self._done('Đã ghi nhận dịch vụ cho khách đang lưu trú.')

    def _calendar(self):
        top = ttk.Frame(self.body)
        top.pack(fill='x')
        start = tk.StringVar(value=str(date.today()))
        days = tk.StringVar(value='7')
        ttk.Label(top, text='Bắt đầu (YYYY-MM-DD)').pack(side='left', padx=(0, 7))
        ttk.Entry(top, textvariable=start, width=16).pack(side='left', padx=(0, 15))
        ttk.Label(top, text='Khoảng ngày').pack(side='left', padx=(0, 7))
        ttk.Combobox(top, textvariable=days, values=['7', '14', '30'], state='readonly',
                     width=5).pack(side='left', padx=(0, 15))
        content = ttk.Frame(self.body)
        content.pack(fill='both', expand=True, pady=(12, 0))

        def load():
            for child in content.winfo_children():
                child.destroy()
            dates, rows = self.c.calendar(start.get(), int(days.get()))
            columns = [('room', 'Phòng', 85)] + [(f'd{i}', label, 145)
                                                for i, label in enumerate(dates)]
            normalized = [dict(room=r['room'], **{f'd{i}': x for i, x in enumerate(r['cells'])})
                          for r in rows]
            add_tree(content, columns, normalized, height=18, row_key='room')

        self._button(top, 'Xem lịch', load, True)
        ttk.Label(self.body, text='“Trống” là có thể bán; mã BK-... là ngày đã giữ/đang ở;'
                  ' “—” là phòng đã ngừng hoạt động.').pack(anchor='w', pady=(9, 0))
        load()
