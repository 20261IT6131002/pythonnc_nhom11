from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, simpledialog
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)
from hotel.views.pages import TABLE_COLUMNS


class AdminScreenMixin:
    def _set_account_kind(self, kind):
        self.account_kind = kind
        self.render('users')

    def _accounts_tab(self):
        all_users = self.c.table('users')
        staff = self.account_kind == 'staff'
        self.rows = [row for row in all_users
                     if (row['role'] in ('admin', 'receptionist')) == staff]
        panel = tk.Frame(self.body, bg=WHITE, highlightbackground=EDGE,
                         highlightthickness=1, padx=20, pady=20)
        panel.pack(fill='both', expand=True)
        toolbar = tk.Frame(panel, bg=WHITE)
        toolbar.pack(fill='x', pady=(0, 17))
        for kind, label in (('staff', 'Nhân viên'), ('customer', 'Khách hàng')):
            active = self.account_kind == kind
            tk.Button(toolbar, text=label, command=lambda kind=kind: self._set_account_kind(kind),
                      cursor='hand2', relief='flat', bd=0,
                      bg=NAVY if active else BACKGROUND,
                      fg=WHITE if active else NAVY,
                      activebackground=SIDEBAR_HOVER, activeforeground=WHITE,
                      font=(FONT, 11, 'bold'), padx=21, pady=12).pack(side='left', padx=(0, 8))
        if staff:
            tk.Button(toolbar, text='+  Thêm tài khoản nhân viên',
                      command=lambda: self._safe(self._add_user), cursor='hand2',
                      relief='flat', bd=0, bg=NAVY, fg=WHITE,
                      activebackground=SIDEBAR_HOVER, activeforeground=WHITE,
                      font=(FONT, 10, 'bold'), padx=15, pady=12).pack(side='right')
        caption = ('Mỗi nhân viên có nút Khóa/Mở và Xóa vĩnh viễn ở bên phải. '
                   'Nhấp đúp vào nhân viên để xem các tùy chọn quản lý thêm.' if staff else
                   'Danh sách tài khoản khách đã đăng ký online — chỉ xem, không sửa hay xóa. '
                   'Khách tại quầy chưa có tài khoản được quản lý trong Hồ sơ khách lưu trú.')
        tk.Label(panel, text=caption, bg=WHITE, fg=MUTED,
                 font=(FONT, 9), anchor='w', wraplength=900).pack(fill='x', pady=(0, 13))

        headings = (('ID', 'Tài khoản / Họ tên', 'Gmail', 'Vai trò', 'Trạng thái', 'Thao tác')
                    if staff else
                    ('ID', 'Tài khoản / Họ tên', 'Gmail', 'SĐT', 'Trạng thái'))
        weights = (0, 2, 2, 1, 1, 2) if staff else (0, 2, 2, 1, 1)
        widths = (28, 105, 125, 68, 90, 192) if staff else (30, 140, 175, 105, 100)
        table_head = tk.Frame(panel, bg='#EAF0F7', padx=10, pady=12)
        table_head.pack(fill='x')
        self._account_grid_columns(table_head, weights, widths)
        for i, heading in enumerate(headings):
            tk.Label(table_head, text=heading, bg='#EAF0F7', fg='#40566D',
                     font=(FONT, 9, 'bold'), anchor='w').grid(row=0, column=i, sticky='ew', padx=6)

        holder = tk.Frame(panel, bg=WHITE)
        holder.pack(fill='both', expand=True)
        scrollbar = ttk.Scrollbar(holder, orient='vertical')
        scrollbar.pack(side='right', fill='y')
        canvas = tk.Canvas(holder, bg=WHITE, highlightthickness=0, bd=0,
                           yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.configure(command=canvas.yview)
        content = tk.Frame(canvas, bg=WHITE)
        window = canvas.create_window((0, 0), window=content, anchor='nw')
        content.bind('<Configure>', lambda _event: canvas.configure(
            scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(window, width=event.width))

        for index, account in enumerate(self.rows):
            bg = WHITE if index % 2 == 0 else '#F6F9FC'
            line = tk.Frame(content, bg=bg, padx=10, pady=15)
            line.pack(fill='x')
            self._account_grid_columns(line, weights, widths)
            def cell(column, content_text, bold=False, color=INK):
                label = tk.Label(line, text=content_text, bg=bg, fg=color,
                                 font=(FONT, 10, 'bold' if bold else 'normal'),
                                 anchor='w', justify='left',
                                 wraplength=155 if column in (1, 2) else 120)
                label.grid(row=0, column=column, sticky='ew', padx=6)
                if staff:
                    label.bind('<Double-Button-1>', lambda _e, row=account:
                               self._safe(lambda: self._open_employee_details(row)))
            cell(0, str(account['id']))
            cell(1, f"{account['username']}\n{account['name']}", bold=True, color=NAVY)
            cell(2, account['email'] or 'Chưa liên kết Gmail')
            cell(3, account['role'] if staff else account['phone'])
            cell(4, account['account_status'],
                 color='#B35C56' if not account['active'] else '#32725D')
            if staff:
                buttons = tk.Frame(line, bg=bg)
                buttons.grid(row=0, column=5, sticky='e', padx=5)
                is_self = account['id'] == self.c.user['id']
                archived = account['account_status'] == 'Ngừng sử dụng'
                for label, callback, danger in (
                    ('Mở' if not account['active'] else 'Khóa',
                     lambda uid=account['id']: self._account_toggle_row(uid), False),
                    ('Xóa vĩnh viễn', lambda uid=account['id']: self._account_delete_row(uid), True),
                ):
                    tk.Button(buttons, text=label,
                              command=lambda action=callback: self._safe(action),
                              state='disabled' if is_self or (archived and not danger) else 'normal',
                              cursor='hand2', relief='flat', bd=0,
                              bg='#FCEBEC' if danger else '#E9EFF7',
                              fg='#AE4E56' if danger else NAVY,
                              activebackground='#E7D1D4' if danger else '#DDE8F4',
                              font=(FONT, 9, 'bold'), padx=8, pady=8).pack(
                                  side='left', padx=(0, 6))

        def wheel(event):
            direction = (-1 if getattr(event, 'num', None) == 4 else 1
                         if getattr(event, 'num', None) == 5 else
                         -1 if getattr(event, 'delta', 0) > 0 else 1)
            canvas.yview_scroll(direction * 2, 'units')

        def bind_wheel(widget):
            widget.bind('<MouseWheel>', wheel, add='+')
            widget.bind('<Button-4>', wheel, add='+')
            widget.bind('<Button-5>', wheel, add='+')
            for child in widget.winfo_children():
                bind_wheel(child)

        bind_wheel(canvas)

    @staticmethod
    def _account_grid_columns(frame, weights, widths):
        for index, (weight, width) in enumerate(zip(weights, widths)):
            frame.grid_columnconfigure(index, weight=weight, minsize=width)

    def _account_toggle_row(self, user_id):
        row = next(row for row in self.rows if row['id'] == user_id)
        verb = 'mở khóa' if not row['active'] else 'khóa'
        if not messagebox.askyesno('Xác nhận',
                f"Bạn muốn {verb} tài khoản nhân viên {row['username']}?",
                parent=self.winfo_toplevel()):
            return
        self.c.toggle_user(user_id)
        self._done(f'Đã {verb} tài khoản.')

    def _account_delete_row(self, user_id):
        row = next(row for row in self.rows if row['id'] == user_id)
        entered = simpledialog.askstring('Xóa vĩnh viễn tài khoản nhân viên',
                    f"Xóa tài khoản {row['username']} khỏi MySQL, không thể khôi phục!\n\n"
                    'Nhập CHÍNH XÁC tên đăng nhập để xác nhận:',
                    parent=self.winfo_toplevel())
        if entered is None:
            return
        if entered != row['username']:
            raise ValueError('Tên đăng nhập xác nhận không khớp. Chưa xóa tài khoản.')
        self.c.delete_staff_permanently(user_id)
        self._done('Đã xóa vĩnh viễn tài khoản nhân viên khỏi MySQL.')

    def _open_employee_details(self, row):
        """Keep secondary staff settings available without crowding the list."""
        values = form_dialog(self, f"Tùy chọn: {row['username']}", [
            ('action', 'Tác vụ', 'Xem hồ sơ',
             ['Xem hồ sơ', 'Sửa hồ sơ', 'Cấp lại mật khẩu tạm', 'Gán / sửa Gmail']),
        ])
        if values is None:
            return
        action = values['action']
        if action == 'Xem hồ sơ':
            success(self, f"Tài khoản: {row['username']}\nTên: {row['name']}\n"
                          f"Vai trò: {row['role']}\nEmail: {row['email']}\n"
                          f"SĐT: {row['phone']}\nChức vụ: {row['position']}")
        elif action == 'Sửa hồ sơ':
            self._edit_employee(row)
        elif action == 'Cấp lại mật khẩu tạm':
            self._reissue_staff(row)
        elif action == 'Gán / sửa Gmail':
            self._staff_email(row)

    def _links_tab(self):
        self.rows = self.c.link_requests()
        panel = tk.Frame(self.body, bg=WHITE, highlightbackground=EDGE,
                         highlightthickness=1, padx=16, pady=16)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Chỉ phê duyệt sau khi đối chiếu giấy tờ hoặc hồ sơ '\
                  'lưu trú với người yêu cầu. SĐT + mã đặt phòng chưa đủ để cấp quyền.').pack(
                      anchor='w', pady=(0, 14))
        bar = ttk.Frame(panel)
        bar.pack(fill='x')
        self._button(bar, 'Làm mới', lambda: self.render('links'))
        self._button(bar, 'Đã kiểm tra — Duyệt', lambda: self._decide_link(True), True)
        self._button(bar, 'Từ chối', lambda: self._decide_link(False))
        self.tree = add_tree(panel, TABLE_COLUMNS['links'], self.rows)

    def _decide_link(self, approve):
        row = self._chosen()
        if approve and not messagebox.askyesno('Xác nhận danh tính',
                'Bạn đã đối chiếu hồ sơ lưu trú và giấy tờ thực tế của người yêu cầu?\n'
                'Chỉ duyệt khi chắc chắn đúng người.', parent=self.winfo_toplevel()):
            return
        self.c.decide_customer_link(row['id'], approve)
        self._done('Đã xử lý yêu cầu liên kết lịch sử.')

    def _reissue_staff(self, row=None):
        row = row if row is not None else self._chosen()
        if row['role'] not in ('admin', 'receptionist'):
            raise ValueError('Chỉ cấp lại mật khẩu tạm cho nhân viên.')
        if not messagebox.askyesno('Cấp lại mật khẩu',
                f"Mật khẩu hiện tại của {row['username']} sẽ mất hiệu lực. "
                'Gửi mật khẩu tạm mới qua Gmail?', parent=self.winfo_toplevel()):
            return
        self.c.reissue_staff_password(row['id'])
        self._done('Đã gửi mật khẩu tạm mới tới Gmail nhân viên.')

    def _staff_email(self, row=None):
        row = row if row is not None else self._chosen()
        values = form_dialog(self, f"Gán Gmail: {row['username']}", [
            ('email', 'Gmail mới sẽ nhận mật khẩu tạm', row['email']),
        ])
        if values is None:
            return
        if not messagebox.askyesno('Thay đổi email nhân viên',
                'Thay email sẽ hủy mật khẩu cũ và gửi mật khẩu tạm mới qua Gmail. '
                'Bạn đã xác nhận địa chỉ với nhân viên?', parent=self.winfo_toplevel()):
            return
        self.c.assign_staff_email(row['id'], values['email'])
        self._done('Đã cập nhật Gmail và gửi thông tin đăng nhập tạm.')

    def _edit_employee(self, row=None):
        row = row if row is not None else self._chosen()
        if row['role'] not in ('admin', 'receptionist'):
            raise ValueError('Chỉ tài khoản nhân viên mới có hồ sơ nhân sự.')
        values = form_dialog(self, f"Hồ sơ nhân viên: {row['username']}", [
            ('phone', 'Số điện thoại', row.get('phone', '')),
            ('position', 'Chức vụ', row.get('position', '')),
        ])
        if values is not None:
            self.c.save_employee(row['id'], values)
            self._done('Đã cập nhật hồ sơ nhân viên.')

    def _reset_user_password(self):
        row = self._chosen()
        values = form_dialog(self, f"Đặt lại mật khẩu: {row['username']}", [
            ('password', 'Mật khẩu mới (tối thiểu 8 ký tự)', '', None, True),
            ('confirmation', 'Nhập lại mật khẩu mới', '', None, True),
        ])
        if values is None:
            return
        if values['password'] != values['confirmation']:
            raise ValueError('Mật khẩu xác nhận không khớp.')
        self.c.reset_user_password(row['id'], values['password'])
        self._done('Đã đặt lại mật khẩu. Hãy bàn giao qua kênh riêng cho chủ tài khoản.')

    def _toggle(self, what):
        row = self._chosen()
        if what == 'room':
            self.c.toggle_room(row['id'])
        else:
            self.c.toggle_user(row['id'])
        self._done('Đã cập nhật trạng thái.')

    def _add_user(self):
        values = form_dialog(self, 'Cấp tài khoản nhân viên qua Gmail',
            [('username', 'Tên đăng nhập', ''), ('name', 'Họ tên', ''),
             ('role', 'Vai trò', 'receptionist', ['receptionist', 'admin']),
             ('phone', 'Số điện thoại nhân viên', ''),
             ('email', 'Gmail nhận mật khẩu tạm', ''),
             ('position', 'Chức vụ', 'Lễ tân')])
        if values is not None:
            self.c.add_user(values)
            self._done('Đã tạo tài khoản và gửi mật khẩu tạm qua Gmail. '\
                       'Nhân viên bắt buộc đổi mật khẩu lần đầu trong 24 giờ.')
