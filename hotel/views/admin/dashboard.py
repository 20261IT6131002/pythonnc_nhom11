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
        ttk.Entry(filters, textvariable=start, width=17).pack(side='left', padx=(0, 15))
        ttk.Label(filters, text='Đến ngày').pack(side='left', padx=(0, 7))
        ttk.Entry(filters, textvariable=end, width=17).pack(side='left', padx=(0, 15))
        info = ttk.Label(self.body, text='', style='Title.TLabel')
        info.pack(anchor='w', pady=(20, 4))
        content = ttk.Frame(self.body)
        content.pack(fill='both', expand=True)

        def load():
            report = self.c.report(start.get(), end.get())
            info.configure(text=f"Đã thu: {report['total']}  •  {report['count']} giao dịch")
            for child in content.winfo_children():
                child.destroy()
            add_tree(content, [('id', 'ID', 65), ('date', 'Ngày thu', 155),
                               ('code', 'Mã đặt', 190), ('amount', 'Số tiền', 190)], report['rows'])

        def export():
            path = filedialog.asksaveasfilename(parent=self, defaultextension='.pdf',
                initialfile='bao_cao_doanh_thu.pdf', filetypes=[('PDF', '*.pdf')])
            if path:
                self.c.export_report(start.get(), end.get(), path)
                success(self, 'Đã xuất báo cáo: ' + path)

        self._button(filters, 'Xem báo cáo', load, True)
        self._button(filters, 'Xuất PDF', export)
        ttk.Label(self.body, text='Số liệu là các khoản tiền nhân viên đã ghi nhận thu trong khoảng ngày.').pack(anchor='w')
        load()
