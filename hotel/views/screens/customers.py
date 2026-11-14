from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class CustomersScreenMixin:
    def _edit_customer(self, edit):
        row = self.c.customer_details(self._chosen()['id']) if edit else {}
        categories = ['Khách mới', 'Khách quen', 'VIP', 'Doanh nghiệp', 'Khách đoàn']
        category_codes = ['normal', 'regular', 'vip', 'corporate', 'group']
        values = form_dialog(self, 'Sửa khách hàng' if edit else 'Thêm khách hàng',
            [('name', 'Họ tên', row.get('name', '')),
             ('phone', 'Điện thoại', row.get('phone', '')),
             ('email', 'Email', row.get('email', '')),
             ('document_no', 'CCCD / Hộ chiếu', row.get('document_no', '')),
             ('category', 'Phân loại', categories[category_codes.index(row.get('category', 'normal'))], categories),
             ('birth_date', 'Ngày sinh (YYYY-MM-DD, có thể bỏ trống)', row.get('birth_date', '')),
             ('address', 'Địa chỉ', row.get('address', '')),
             ('organization', 'Đoàn / doanh nghiệp', row.get('organization', '')),
             ('preferences', 'Sở thích', row.get('preferences', '')),
             ('special_requests', 'Yêu cầu đặc biệt', row.get('special_requests', ''))])
        if values is not None:
            values['category'] = category_codes[categories.index(values['category'])]
            self.c.save_customer(values, row.get('id'))
            self._done()

    def _customer_history(self):
        detail = self.c.customer_details(self._chosen()['id'])
        dialog = tk.Toplevel(self)
        dialog.title(f"Lịch sử khách {detail['id']} — {detail['name']}")
        dialog.geometry('980x530')
        dialog.transient(self.winfo_toplevel())
        panel = ttk.Frame(dialog, padding=18)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text=f"{detail['booking_count']} đơn · {detail['stay_count']} lượt lưu trú · "
                  f"Đã thanh toán {detail['paid_total']}", style='FormTitle.TLabel').pack(anchor='w')
        add_tree(panel, [('code', 'Mã đặt', 160), ('room', 'Phòng', 65),
                        ('checkin', 'Ngày nhận', 110), ('checkout', 'Ngày trả', 110),
                        ('status', 'Trạng thái', 120), ('checked_in_at', 'Nhận thực tế (UTC)', 180),
                        ('checked_out_at', 'Trả thực tế (UTC)', 180)], detail['history'])
        ttk.Button(panel, text='Đóng', command=dialog.destroy).pack(anchor='e', pady=(12, 0))

    def _customers_tab(self):
        query = tk.StringVar(value=getattr(self, 'customer_query', ''))
        bar = ttk.Frame(self.body)
        bar.pack(fill='x', pady=(0, 12))
        ttk.Label(bar, text='Tên / SĐT / email / mã khách').pack(side='left', padx=(0, 8))
        entry = ttk.Entry(bar, textvariable=query, width=32)
        entry.pack(side='left', padx=(0, 8))

        def search():
            self.customer_query = query.get()
            self.render('customers')

        self._button(bar, 'Tìm kiếm', search, True)
        entry.bind('<Return>', lambda _event: self._safe(search))
        self._table_tab('customers')

    def _booking_guests(self):
        booking = self._chosen()
        dialog = tk.Toplevel(self)
        dialog.title(f"Người lưu trú — {booking['code']} / Phòng {booking['room']}")
        dialog.geometry('940x520')
        dialog.transient(self.winfo_toplevel())
        panel = ttk.Frame(dialog, padding=18)
        panel.pack(fill='both', expand=True)
        bar = ttk.Frame(panel)
        bar.pack(fill='x')
        content = ttk.Frame(panel)
        content.pack(fill='both', expand=True)
        rows, tree = [], None

        def load():
            nonlocal rows, tree
            for child in content.winfo_children():
                child.destroy()
            rows = self.c.booking_guests(booking['id'])
            ttk.Label(content, text=f"Đã khai báo {len(rows)} / {booking['guests']} người. "
                      'Nhập cả người đại diện nếu người đó cùng lưu trú.').pack(anchor='w', pady=(12, 0))
            tree = add_tree(content, [('name', 'Họ tên', 200), ('document_no', 'Giấy tờ', 160),
                ('birth_date', 'Ngày sinh', 110), ('nationality', 'Quốc tịch', 120),
                ('primary_label', 'Người đại diện', 130)],
                [dict(row, primary_label='Có' if row['is_primary'] else 'Không') for row in rows])

        def edit(existing=False):
            row = {}
            if existing:
                if not tree.selection():
                    raise ValueError('Hãy chọn một người lưu trú.')
                row = next(item for item in rows if str(item['id']) == tree.selection()[0])
            values = form_dialog(dialog, 'Thông tin người lưu trú', [
                ('name', 'Họ tên', row.get('name', '')),
                ('document_no', 'CCCD / Hộ chiếu', row.get('document_no', '')),
                ('birth_date', 'Ngày sinh (YYYY-MM-DD)', row.get('birth_date', '')),
                ('nationality', 'Quốc tịch', row.get('nationality', 'Việt Nam')),
                ('is_primary', 'Người đại diện', 'Có' if row.get('is_primary') else 'Không', ['Có', 'Không']),
            ])
            if values is not None:
                values['is_primary'] = values['is_primary'] == 'Có'
                self.c.save_booking_guest(booking['id'], values, row.get('id'))
                load()

        self._button(bar, 'Thêm người lưu trú', edit, True)
        self._button(bar, 'Sửa thông tin', lambda: edit(True))
        load()
