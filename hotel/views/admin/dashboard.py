from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class AdminReportsMixin:
    def _reports(self):
        filters = ttk.Frame(self.body)
        filters.pack(fill='x')
        today = date.today()
        start = tk.StringVar(value=str(today.replace(day=1)))
        end = tk.StringVar(value=str(today))
        ttk.Label(filters, text='Từ ngày').pack(side='left', padx=(0, 7))
        ttk.Entry(filters, textvariable=start, width=15).pack(side='left', padx=(0, 12))
        ttk.Label(filters, text='Đến ngày').pack(side='left', padx=(0, 7))
        ttk.Entry(filters, textvariable=end, width=15).pack(side='left', padx=(0, 15))

        kpi_frame = tk.Frame(self.body, bg=BACKGROUND)
        kpi_frame.pack(fill='x', pady=(16, 12))

        notebook = ttk.Notebook(self.body)
        notebook.pack(fill='both', expand=True, pady=(6, 0))

        tab_tx = ttk.Frame(notebook, padding=8)
        tab_rooms = ttk.Frame(notebook, padding=8)
        tab_methods = ttk.Frame(notebook, padding=8)

        notebook.add(tab_tx, text='  Tất cả giao dịch  ')
        notebook.add(tab_rooms, text='  Cơ cấu Loại phòng  ')
        notebook.add(tab_methods, text='  Phương thức thanh toán  ')

        def load():
            rep = self.c.comprehensive_financial_report(start.get(), end.get())

            for child in kpi_frame.winfo_children():
                child.destroy()

            cards = [
                ('Doanh thu thanh toán', rep['payments_total'], f"{rep['payments_count']} GD hóa đơn"),
                ('Tiền đặt cọc nhận vào', rep['deposits_total'], f"{rep['deposits_count']} GD cọc"),
                ('Tiền đã hoàn lại (Refund)', f"-{rep['refunds_total']}", f"{rep['refunds_count']} GD hoàn"),
                ('DOANH THU THUẦN', rep['net_revenue'], 'Tổng thu trừ hoàn tiền'),
                ('Công nợ còn thiếu', rep['total_due'], f"{rep['invoices_count']} HĐ trong kỳ"),
            ]

            for idx, (label, val, note) in enumerate(cards):
                cell = tk.Frame(kpi_frame, bg=WHITE, highlightbackground=EDGE,
                                highlightthickness=1, padx=12, pady=10)
                cell.grid(row=0, column=idx, sticky='nsew', padx=4)
                text(cell, label, 8, MUTED, WHITE, 'bold').pack(anchor='w')
                is_net = label == 'DOANH THU THUẦN'
                is_refund = label.startswith('Tiền đã hoàn')
                color = '#2e7d32' if is_net else ('#c45c60' if is_refund else NAVY)
                text(cell, str(val), 14 if is_net else 13, color, WHITE, 'bold').pack(anchor='w', pady=(4, 3))
                text(cell, note, 8, '#a1afbb', WHITE).pack(anchor='w')
            for i in range(len(cards)):
                kpi_frame.grid_columnconfigure(i, weight=1)

            # Tab 1: Giao dịch
            for c in tab_tx.winfo_children():
                c.destroy()
            tx_cols = [('id', 'Mã GD', 80), ('type', 'Loại', 85), ('code', 'Mã đơn', 130),
                       ('customer', 'Khách hàng', 150), ('amount', 'Số tiền', 130),
                       ('method', 'Hình thức', 110), ('date', 'Thời gian', 135),
                       ('reference', 'Chi tiết / Ghi chú', 190)]
            add_tree(tab_tx, tx_cols, rep['transactions'])

            # Tab 2: Loại phòng
            for c in tab_rooms.winfo_children():
                c.destroy()
            room_cols = [('name', 'Loại phòng', 160), ('count', 'Số lượt thuê', 90),
                         ('room_amount', 'Doanh thu phòng', 150),
                         ('services_amount', 'Doanh thu dịch vụ', 150),
                         ('total', 'Tổng cộng', 160)]
            add_tree(tab_rooms, room_cols, rep['room_types'])

            # Tab 3: Phương thức
            for c in tab_methods.winfo_children():
                c.destroy()
            method_cols = [('name', 'Phương thức thanh toán', 180),
                           ('payment', 'Thu thanh toán', 140),
                           ('deposit', 'Thu đặt cọc', 140),
                           ('refund', 'Chi hoàn tiền', 140),
                           ('net', 'Thực thu thuần', 150)]
            add_tree(tab_methods, method_cols, rep['methods'])

        def export_comprehensive():
            path = filedialog.asksaveasfilename(
                parent=self, defaultextension='.pdf',
                initialfile=f"bao_cao_tai_chinh_{start.get()}_{end.get()}.pdf",
                filetypes=[('PDF', '*.pdf')])
            if path:
                self.c.export_comprehensive_financial_report(start.get(), end.get(), path)
                success(self, 'Đã xuất Báo cáo tài chính toàn diện PDF:\n' + path)

        def export_basic():
            path = filedialog.asksaveasfilename(
                parent=self, defaultextension='.pdf',
                initialfile=f"bao_cao_doanh_thu_{start.get()}_{end.get()}.pdf",
                filetypes=[('PDF', '*.pdf')])
            if path:
                self.c.export_report(start.get(), end.get(), path)
                success(self, 'Đã xuất báo cáo doanh thu cơ bản:\n' + path)

        self._button(filters, 'Xem báo cáo', load, True)
        self._button(filters, 'Xuất PDF Báo cáo toàn diện', export_comprehensive)
        self._button(filters, 'Xuất PDF Giao dịch', export_basic)

        load()
