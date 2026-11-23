from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog, messagebox
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT,
                                          INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE,
                                          brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class BillingScreenMixin:
    def _invoice(self):
        row = self._chosen()
        invoice_id = self.c.make_invoice(row['id'])
        self._done(f'Đã chốt hóa đơn số {invoice_id}. Sang mục Hóa đơn để thu tiền.')

    def _payment(self):
        row = self._chosen()
        values = form_dialog(self, 'Ghi nhận thanh toán hóa đơn',
            [('amount', 'Số tiền thanh toán (VND)', ''),
             ('method', 'Hình thức', 'cash', ['cash', 'bank_transfer', 'card_manual']),
             ('reference', 'Mã tham chiếu / Số hóa đơn ngân hàng', '')])
        if values is not None:
            self.c.pay(row['id'], values['amount'], values['method'], values['reference'])
            self._done('Đã ghi nhận thanh toán thành công vào hệ thống.')

    def _invoice_pdf(self):
        row = self._chosen()
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.pdf',
            initialfile=f"hoa_don_{row['code']}.pdf", filetypes=[('PDF', '*.pdf')])
        if path:
            self.c.export_invoice(row['id'], path)
            success(self, 'Đã lưu hóa đơn PDF tại:\n' + path)

    def _invoice_email(self):
        row = self._chosen()
        values = form_dialog(self, f"Gửi hóa đơn đơn #{row['code']} qua Email",
            [('email', 'Email người nhận', row.get('customer_email', ''))])
        if values is not None:
            self.c.send_invoice_email(row['id'], values.get('email'))
            success(self, f"Đã gửi hóa đơn PDF tới: {values.get('email')}")

    def _invoice_details(self):
        row = self._chosen()
        info = self.c.get_invoice_details(row['id'])

        win = tk.Toplevel(self)
        win.title(f"Chi tiết tài chính hóa đơn #{info['id']} - Đơn {info['code']}")
        win.geometry('680x600')
        win.configure(bg=BACKGROUND)
        win.transient(self.winfo_toplevel())
        win.grab_set()

        body = ttk.Frame(win, padding=20)
        body.pack(fill='both', expand=True)

        text(body, f"HÓA ĐƠN #{info['id']} - ĐƠN {info['code']}", 15, NAVY, BACKGROUND, 'bold').pack(anchor='w')
        text(body, f"Khách hàng: {info['customer']}  |  Phòng: {info['room']}", 10, MUTED, BACKGROUND).pack(anchor='w', pady=(2, 14))

        summary = tk.Frame(body, bg=WHITE, highlightthickness=1, highlightbackground=EDGE, padx=14, pady=12)
        summary.pack(fill='x', pady=(0, 14))
        for label, val in [('Tiền phòng', info['room_amount']),
                           ('Tiền dịch vụ', info['services_amount']),
                           ('Giảm giá', info['discount_amount']),
                           ('TỔNG CỘNG', info['total_amount']),
                           ('Đã đặt cọc', info['deposit_total']),
                           ('Đã thanh toán thêm', info['payment_total']),
                           ('Đã hoàn lại', info['refund_total']),
                           ('Thực tế đã thu', info['net_paid']),
                           ('CÒN THIẾU', info['due'])]:
            line = tk.Frame(summary, bg=WHITE)
            line.pack(fill='x', pady=2)
            is_bold = label in ('TỔNG CỘNG', 'CÒN THIẾU', 'Thực tế đã thu')
            text(line, label, 10, NAVY if is_bold else INK, WHITE, 'bold' if is_bold else 'normal').pack(side='left')
            color = '#c45c60' if label == 'CÒN THIẾU' and val != '0 VND' else (GOLD if is_bold else INK)
            text(line, val, 10, color, WHITE, 'bold' if is_bold else 'normal').pack(side='right')

        # Lịch sử các khoản thanh toán
        text(body, 'Lịch sử thanh toán & đặt cọc', 11, NAVY, BACKGROUND, 'bold').pack(anchor='w', pady=(6, 4))
        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill='both', expand=True)
        tx_rows = []
        for d in info['deposits']:
            tx_rows.append({'id': f"DEP-{d['id']}", 'type': 'Tiền cọc', 'amount': d['amount'],
                            'method': d['method'], 'date': d['date'], 'note': d['reference'] or d['status']})
        for p in info['payments']:
            tx_rows.append({'id': f"PAY-{p['id']}", 'type': 'Thanh toán', 'amount': p['amount'],
                            'method': p['method'], 'date': p['date'], 'note': p['reference'] or '-'})
        for r in info['refunds']:
            tx_rows.append({'id': f"REF-{r['id']}", 'type': 'Hoàn tiền', 'amount': f"-{r['amount']}",
                            'method': r['method'], 'date': r['date'], 'note': r['reason'] or '-'})

        add_tree(tree_frame, [('id', 'Mã GD', 75), ('type', 'Loại', 85),
                              ('amount', 'Số tiền', 115), ('method', 'Hình thức', 90),
                              ('date', 'Thời gian', 130), ('note', 'Ghi chú', 130)],
                 tx_rows, height=7)

        btn_box = ttk.Frame(body)
        btn_box.pack(fill='x', pady=(14, 0))
        ttk.Button(btn_box, text='Đóng', command=win.destroy).pack(side='right')

    def _record_deposit(self):
        """Mở form thu tiền đặt cọc."""
        # Lấy danh sách booking chưa thanh toán hoặc đang active
        choices = [f"{b['id']} - {b['code']} / {b['customer']} (P.{b['room']})"
                   for b in self.c.table('bookings') if b['status'] in ('pending', 'confirmed', 'checked_in')]
        if not choices:
            raise ValueError('Không có đơn đặt phòng nào cần thu cọc.')
        values = form_dialog(self, 'Ghi nhận thu tiền đặt cọc',
            [('booking', 'Đơn đặt phòng', choices[0], choices),
             ('amount', 'Số tiền cọc (VND)', ''),
             ('method', 'Hình thức thu', 'cash', ['cash', 'bank_transfer', 'card_manual']),
             ('reference', 'Mã giao dịch / Ngân hàng', ''),
             ('notes', 'Ghi chú', '')])
        if values is not None:
            booking_id = choice_id(values['booking'])
            deposit_id = self.c.record_deposit(booking_id, values['amount'], values['method'],
                                               values['reference'], values['notes'])
            self._done(f"Đã ghi nhận đặt cọc thành công! (Mã phiếu: DEP-{deposit_id})")

    def _deposit_pdf(self):
        row = self._chosen()
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.pdf',
            initialfile=f"phieu_coc_{row['code']}.pdf", filetypes=[('PDF', '*.pdf')])
        if path:
            self.c.export_deposit_receipt(row['id'], path)
            success(self, 'Đã xuất phiếu cọc PDF:\n' + path)

    def _deposit_email(self):
        row = self._chosen()
        values = form_dialog(self, f"Gửi phiếu thu cọc đơn #{row['code']}",
            [('email', 'Email khách hàng', '')])
        if values is not None:
            self.c.send_deposit_email(row['id'], values.get('email'))
            success(self, f"Đã gửi email phiếu cọc tới: {values.get('email')}")

    def _record_refund(self):
        """Mở form hoàn tiền cho đơn."""
        choices = [f"{b['id']} - {b['code']} / {b['customer']}"
                   for b in self.c.table('bookings')]
        if not choices:
            raise ValueError('Chưa có đơn đặt phòng trong hệ thống.')

        chosen_booking = form_dialog(self, 'Chọn đơn cần hoàn tiền',
            [('booking', 'Đơn đặt phòng', choices[0], choices)])
        if chosen_booking is None:
            return

        b_id = choice_id(chosen_booking['booking'])
        suggest = self.c.suggest_refund(b_id)
        limit = suggest['refundable_limit']
        if limit <= 0:
            raise ValueError('Đơn này chưa có khoản thu nào để hoàn lại.')

        values = form_dialog(self, 'Xử lý hoàn tiền cho khách',
            [('policy', 'Quy định áp dụng', suggest['policy']),
             ('amount', f"Số tiền hoàn (Tối đa {limit:,.0f} VND)", str(int(suggest['suggested_amount']))),
             ('method', 'Hình thức hoàn', 'bank_transfer', ['bank_transfer', 'cash', 'card_manual']),
             ('reason', 'Lý do hoàn tiền', 'Hủy phòng theo chính sách khách sạn')])
        if values is not None:
            ref_id = self.c.record_refund(b_id, values['amount'], values['method'], values['reason'])
            self._done(f"Đã xử lý hoàn tiền thành công! (Mã phiếu: REF-{ref_id})")

    def _refund_pdf(self):
        row = self._chosen()
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.pdf',
            initialfile=f"phieu_hoan_{row['code']}.pdf", filetypes=[('PDF', '*.pdf')])
        if path:
            self.c.export_refund_receipt(row['id'], path)
            success(self, 'Đã xuất phiếu chi hoàn tiền PDF:\n' + path)

    def _refund_email(self):
        row = self._chosen()
        values = form_dialog(self, f"Gửi thông báo hoàn tiền đơn #{row['code']}",
            [('email', 'Email khách hàng', '')])
        if values is not None:
            self.c.send_refund_email(row['id'], values.get('email'))
            success(self, f"Đã gửi email phiếu hoàn tiền tới: {values.get('email')}")

    def _refund_deposit(self):
        """Hoàn cọc trực tiếp từ dòng cọc đã chọn."""
        row = self._chosen()
        values = form_dialog(self, f"Hoàn cọc đơn #{row['code']}",
            [('amount', 'Số tiền hoàn lại (VND)', row['amount'].replace(' VND', '').replace(',', '')),
             ('method', 'Hình thức hoàn', 'bank_transfer', ['bank_transfer', 'cash', 'card_manual']),
             ('reason', 'Lý do hoàn cọc', 'Khách hủy đơn / Hoàn cọc')])
        if values is not None:
            # Tìm booking_id từ mã đơn
            bookings = [b for b in self.c.table('bookings') if b['code'] == row['code']]
            if not bookings:
                raise ValueError('Không tìm thấy đơn tương ứng.')
            self.c.record_refund(bookings[0]['id'], values['amount'], values['method'], values['reason'])
            self._done('Đã ghi nhận hoàn cọc cho khách hàng.')

    def _refund_invoice(self):
        """Hoàn tiền từ dòng hóa đơn đã chọn."""
        row = self._chosen()
        suggest = self.c.suggest_refund(row['id'])
        bookings = [b for b in self.c.table('bookings') if b['code'] == row['code']]
        if not bookings:
            raise ValueError('Không tìm thấy đơn tương ứng.')
        b_id = bookings[0]['id']
        suggest = self.c.suggest_refund(b_id)
        limit = suggest['refundable_limit']
        if limit <= 0:
            raise ValueError('Hóa đơn này không có số dư để hoàn lại.')

        values = form_dialog(self, f"Hoàn tiền hóa đơn #{row['id']} - Đơn {row['code']}",
            [('policy', 'Chính sách hoàn tiền', suggest['policy']),
             ('amount', f"Số tiền hoàn (Tối đa {limit:,.0f} VND)", str(int(suggest['suggested_amount']))),
             ('method', 'Phương thức', 'bank_transfer', ['bank_transfer', 'cash', 'card_manual']),
             ('reason', 'Lý do hoàn', 'Điều chỉnh hóa đơn / Hoàn tiền')])
        if values is not None:
            self.c.record_refund(b_id, values['amount'], values['method'], values['reason'])
            self._done('Đã hoàn tiền thành công!')

