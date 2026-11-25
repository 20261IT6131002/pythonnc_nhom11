from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)
from hotel.views.components.service_forms import request_service_dialog
from hotel.views.components.service_details import show_booking_services


class ServicesScreenMixin:
    def _edit_service(self, edit):
        row = self._chosen() if edit else {}
        values = form_dialog(self, 'Sửa dịch vụ' if edit else 'Thêm dịch vụ',
            [('name', 'Tên dịch vụ', row.get('name', '')),
             ('price', 'Đơn giá (VND)', row.get('price', '50000')),
             ('category', 'Nhóm dịch vụ', row.get('category', 'Tiện ích')),
             ('unit', 'Đơn vị tính', row.get('unit', 'lượt')),
             ('description', 'Mô tả', row.get('description', '')),
             ('requires_schedule', 'Cần đặt lịch hẹn', 'Có' if row.get('requires_schedule') else 'Không', ['Có', 'Không']),
             ('duration_minutes', 'Thời lượng mỗi lượt (phút)', row.get('duration_minutes', 60)),
             ('slot_capacity', 'Số suất phục vụ cùng lúc', row.get('slot_capacity', 1)),
             ('active', 'Đang cung cấp', 'Có' if row.get('active', True) else 'Không', ['Có', 'Không'])])
        if values is not None:
            values['active'] = values['active'] == 'Có'
            values['requires_schedule'] = values['requires_schedule'] == 'Có'
            self.c.save_service(values, row.get('id'))
            self._done()

    def _request_service(self, from_booking=False):
        row_id = self._chosen()['id'] if from_booking else None
        if request_service_dialog(self, self.c, booking_id=row_id) is not None:
            self._done('Đã tạo yêu cầu dịch vụ chờ xác nhận.')

    def _service_order_status(self, status):
        self.c.set_service_order_status(self._chosen()['id'], status)
        self._done('Đã cập nhật trạng thái yêu cầu dịch vụ.')

    def _service_orders_tab(self):
        saved = getattr(self, 'service_order_filters', {})
        statuses = {'Tất cả': '', 'Chờ xác nhận': 'pending', 'Đã xác nhận': 'confirmed',
                    'Đã hoàn thành': 'completed', 'Đã hủy': 'cancelled'}
        query = tk.StringVar(value=saved.get('query', ''))
        status = tk.StringVar(value=next(label for label, value in statuses.items()
                                         if value == saved.get('status', '')))
        date_from = tk.StringVar(value=saved.get('date_from', ''))
        date_to = tk.StringVar(value=saved.get('date_to', ''))
        filters = ttk.Frame(self.body)
        filters.pack(fill='x', pady=(0, 10))
        ttk.Label(filters, text='Đơn / phòng / khách / SĐT / dịch vụ').grid(row=0, column=0, sticky='w')
        entry = ttk.Entry(filters, textvariable=query, width=23)
        entry.grid(row=0, column=1, padx=(8, 18), pady=5, sticky='w')
        ttk.Label(filters, text='Trạng thái').grid(row=0, column=2, sticky='w')
        ttk.Combobox(filters, textvariable=status, values=list(statuses), state='readonly', width=18).grid(
            row=0, column=3, padx=(8, 0), sticky='w')
        ttk.Label(filters, text='Ngày tạo từ (YYYY-MM-DD, giờ VN)').grid(row=1, column=0, sticky='w')
        ttk.Entry(filters, textvariable=date_from, width=16).grid(row=1, column=1, padx=(8, 18), pady=5, sticky='w')
        ttk.Label(filters, text='Đến ngày').grid(row=1, column=2, sticky='w')
        ttk.Entry(filters, textvariable=date_to, width=18).grid(row=1, column=3, padx=(8, 0), sticky='w')
        actions = ttk.Frame(self.body)
        actions.pack(fill='x', pady=(0, 10))

        def apply():
            self.service_order_filters = dict(query=query.get(), status=statuses[status.get()],
                                             date_from=date_from.get(), date_to=date_to.get())
            self.render('service_orders')

        def clear():
            self.service_order_filters = {}
            self.render('service_orders')

        self._button(actions, 'Áp dụng bộ lọc', apply, True)
        self._button(actions, 'Xóa bộ lọc', clear)
        entry.bind('<Return>', lambda _event: self._safe(apply))
        self._table_tab('service_orders')

    def _booking_service_details(self, from_order=False):
        row = self._chosen()
        show_booking_services(self, self.c, row['booking_id'] if from_order else row['id'])
