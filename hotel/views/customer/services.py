from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)
from hotel.views.components.service_forms import request_service_dialog
from hotel.views.pages import TABLE_COLUMNS


class CustomerServicesMixin:
    def show_services(self):
        self._clear()
        self._banner('DỊCH VỤ TIỆN ÍCH', 'Chăm sóc bạn trong từng chi tiết',
                     'Ẩm thực, giặt là và các tiện ích dành cho kỳ nghỉ GrandStay.')
        self._service_features()
        section = self._section()
        text(section, 'Dịch vụ đang cung cấp', 19, NAVY, WHITE,
             'bold').pack(anchor='w', pady=(0, 20))
        for service in self.c.service_catalog(public=True):
            line = tk.Frame(section, bg=WHITE, highlightbackground=EDGE,
                            highlightthickness=1, padx=18, pady=15)
            line.pack(fill='x', pady=5)
            text(line, service['name'], 12, NAVY, WHITE, 'bold').pack(side='left')
            if self.c.user and self.c.user['role'] == 'customer':
                solid_button(line, 'Đăng ký', lambda sid=service['id']: self.request_customer_service(sid),
                             light=True).pack(side='right', padx=(16, 0))
            text(line, f"{service['price']}đ/{service['unit']}", 12, GOLD, WHITE, 'bold').pack(side='right')
            if service['requires_schedule']:
                text(line, f"Lịch hẹn {service['duration_minutes']} phút · {service['slot_capacity']} suất",
                     10, MUTED, WHITE).pack(side='left', padx=16)
        if self.c.user and self.c.user['role'] == 'customer':
            self._customer_service_orders()
        self._public_promotions()
        self._footer()

    def request_customer_service(self, service_id):
        try:
            if request_service_dialog(self, self.c, service_id=service_id) is not None:
                success(self, 'Đã gửi yêu cầu dịch vụ. Lễ tân sẽ xác nhận và ghi nhận khi hoàn thành.')
                self.show_services()
        except Exception as exc:
            error(self, exc)

    def _customer_service_orders(self):
        section = self._section()
        text(section, 'Yêu cầu dịch vụ của tôi', 18, NAVY, WHITE, 'bold').pack(anchor='w')
        rows = self.c.service_orders()
        tree = add_tree(section, [column for column in TABLE_COLUMNS['service_orders']
                                 if column[0] != 'customer'], rows, height=7)

        def cancel():
            try:
                if not tree.selection():
                    raise ValueError('Chọn yêu cầu chờ xác nhận cần hủy.')
                self.c.set_service_order_status(int(tree.selection()[0]), 'cancelled')
                self.show_services()
            except Exception as exc:
                error(self, exc)

        solid_button(section, 'Hủy yêu cầu đang chờ', cancel, light=True).pack(anchor='w', pady=(12, 0))

    def _public_promotions(self):
        section = self._section()
        text(section, 'Khuyến mãi tiền phòng', 18, NAVY, WHITE, 'bold').pack(anchor='w', pady=(0, 12))
        promotions = self.c.promotions(public=True)
        if not promotions:
            text(section, 'Hiện chưa có chương trình khuyến mãi hiệu lực.', 11, MUTED, WHITE).pack(anchor='w')
        for row in promotions:
            discount = f"{row['value']}%" if row['discount_type'] == 'percent' else f"{row['value']}đ"
            text(section, f"{row['code']} · {row['name']} · Giảm {discount} tiền phòng · "
                 f"Đơn từ {row['minimum_amount']}đ · Hạn {row['ends_on']}",
                 11, NAVY, WHITE, wraplength=950).pack(anchor='w', pady=5)
        text(section, 'Mỗi đơn dùng một mã; lượt đã sử dụng được giữ cả khi hủy đơn.',
             10, MUTED, WHITE).pack(anchor='w', pady=(8, 0))
