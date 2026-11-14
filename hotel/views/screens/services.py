from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)
from hotel.views.components.service_forms import request_service_dialog


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
