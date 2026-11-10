"""GrandStay sign-in, email registration and OTP recovery screens (N1)."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from hotel.views.components.theme import (BACKGROUND, EDGE, FONT, GOLD, GOLD_LIGHT,
                                           INK, MUTED, NAVY, WHITE, brand, hotel_art)
from hotel.views.components.widget_helpers import error, form_dialog


DEEP_BLUE = '#102F49'
PANEL_BG = '#FFFFFF'
FIELD_BG = '#F5F8FC'
PALE_BLUE = '#E8F1F9'


class LoginView(tk.Frame):
    def __init__(self, parent, controller, app):
        super().__init__(parent, bg=WHITE)
        self.c, self.app = controller, app
        self.mode = 'login'
        self.fields = {}

        header = tk.Frame(self, bg=WHITE, height=78,
                          highlightbackground=EDGE, highlightthickness=1)
        header.pack(fill='x')
        header.pack_propagate(False)
        brand(header, tagline='HOTEL & RESORT').pack(side='left', padx=38, pady=15)
        tk.Button(header, text='←  Về trang chủ', command=app.show_guest,
                  font=(FONT, 10, 'bold'), bg=WHITE, fg=DEEP_BLUE,
                  activeforeground=GOLD, bd=0, relief='flat',
                  cursor='hand2').pack(side='right', padx=40)

        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill='both', expand=True)
        # Tkinter's pack(expand=True) does not guarantee equal halves when
        # children request different widths. A uniform grid does (50/50).
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1, uniform='auth_halves')
        body.grid_columnconfigure(1, weight=1, uniform='auth_halves')
        self.left = tk.Frame(body, bg=DEEP_BLUE)
        self.left.grid(row=0, column=0, sticky='nsew')
        left_text = tk.Frame(self.left, bg=DEEP_BLUE, padx=38, pady=30)
        left_text.pack(fill='x')
        self._label(left_text, 'GRANDSTAY  •  SECURE ACCESS', 10, GOLD_LIGHT,
                    DEEP_BLUE, 'bold').pack(anchor='w', pady=(0, 17))
        self._label(left_text, 'Trải nghiệm lưu trú\ntrọn vẹn hơn.', 25, WHITE,
                    DEEP_BLUE, 'bold', justify='left').pack(anchor='w')
        self._label(left_text, 'Chào mừng bạn đến với GrandStay.\n'
                    'Quản lý chuyến đi dễ dàng và bảo mật.', 10, '#BBCCDA',
                    DEEP_BLUE, justify='left').pack(anchor='w', pady=(14, 0))
        illustration = tk.Canvas(self.left, bg=DEEP_BLUE, highlightthickness=0, height=290)
        illustration.pack(fill='both', expand=True, padx=22, pady=(4, 8))
        illustration.bind('<Configure>', lambda ev: hotel_art(
            illustration, max(50, ev.width), max(50, ev.height)))

        self.right = tk.Frame(body, bg=FIELD_BG)
        self.right.grid(row=0, column=1, sticky='nsew')
        # The registration form is taller than the minimum window height;
        # scrolling prevents the OTP/submit actions being clipped off-screen.
        self.form_scroll = ttk.Scrollbar(self.right, orient='vertical')
        self.form_scroll.pack(side='right', fill='y')
        self.form_canvas = tk.Canvas(self.right, bg=FIELD_BG,
                                     highlightthickness=0, borderwidth=0,
                                     yscrollcommand=self.form_scroll.set)
        self.form_canvas.pack(side='left', fill='both', expand=True)
        self.form_scroll.configure(command=self.form_canvas.yview)
        self.panel = tk.Frame(self.form_canvas, bg=PANEL_BG, padx=36, pady=27,
                              highlightthickness=1, highlightbackground='#DFE7EF')
        self.panel_window = self.form_canvas.create_window(0, 24, window=self.panel,
                                                            anchor='n')
        self.form_canvas.bind('<Configure>', self._fit_panel)
        self.panel.bind('<Configure>', self._fit_panel)
        self._render()

    @staticmethod
    def _label(parent, content, size=10, fg=INK, bg=WHITE,
               weight='normal', **options):
        return tk.Label(parent, text=content, bg=bg, fg=fg,
                        font=(FONT, size, weight), **options)

    def _heading(self, eyebrow, title, description):
        self._label(self.panel, eyebrow.upper(), 10, '#9F793F', WHITE, 'bold').pack(
            anchor='w', pady=(14, 8))
        self._label(self.panel, title, 25, DEEP_BLUE, WHITE, 'bold').pack(anchor='w')
        self._label(self.panel, description, 10, MUTED, WHITE,
                    justify='left', wraplength=390).pack(anchor='w', pady=(8, 17))

    def _field(self, key, caption, secret=False, initial=''):
        self._label(self.panel, caption, 10, '#40546A', WHITE, 'bold').pack(
            anchor='w', pady=(5, 4))
        item = ttk.Entry(self.panel, width=36, font=(FONT, 11),
                         show='•' if secret else '')
        item.insert(0, initial)
        item.pack(fill='x', ipady=6, pady=(0, 4))
        self.fields[key] = item
        return item

    def _button(self, caption, callback, primary=True):
        button = tk.Button(self.panel, text=caption, command=callback,
                           bg=DEEP_BLUE if primary else PALE_BLUE,
                           fg=WHITE if primary else DEEP_BLUE,
                           activebackground='#285477' if primary else '#D4E7F6',
                           activeforeground=WHITE if primary else DEEP_BLUE,
                           relief='flat', bd=0, cursor='hand2',
                           font=(FONT, 11, 'bold'), padx=16, pady=11)
        button.pack(fill='x', pady=(8, 0))
        return button

    def _link(self, caption, target):
        tk.Button(self.panel, text=caption,
                  command=lambda: self._switch(target), bg=WHITE,
                  fg=DEEP_BLUE, activeforeground=GOLD,
                  relief='flat', bd=0, cursor='hand2',
                  font=(FONT, 10, 'bold')).pack(pady=(10, 0))

    def _tabs(self):
        tabs = tk.Frame(self.panel, bg='#EDF2F7', padx=5, pady=5)
        tabs.pack(fill='x', pady=(0, 10))
        tabs.grid_columnconfigure(0, weight=1, uniform='auth_tabs')
        tabs.grid_columnconfigure(1, weight=1, uniform='auth_tabs')
        for col, (mode, caption) in enumerate((('login', 'ĐĂNG NHẬP'),
                                                ('register', 'ĐĂNG KÝ'))):
            active = self.mode == mode
            tk.Button(tabs, text=caption, command=lambda mode=mode: self._switch(mode),
                      font=(FONT, 11, 'bold'), cursor='hand2', relief='flat', bd=0,
                      bg=DEEP_BLUE if active else '#EDF2F7',
                      fg=WHITE if active else '#4F657A',
                      activebackground='#285477', activeforeground=WHITE,
                      pady=12).grid(row=0, column=col, sticky='ew')

    def _fit_panel(self, _event=None):
        """Center a short form; allow vertical scrolling for longer forms."""
        width = self.form_canvas.winfo_width()
        height = self.form_canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        self.form_canvas.itemconfigure(self.panel_window, width=max(1, width - 52))
        form_height = self.panel.winfo_reqheight()
        top = max(22, (height - form_height) // 2)
        self.form_canvas.coords(self.panel_window, width // 2, top)
        self.form_canvas.configure(scrollregion=(0, 0, width,
                                   max(height, top + form_height + 22)))

    def _on_wheel(self, event):
        if getattr(event, 'num', None) in (4, 5):
            direction = -1 if event.num == 4 else 1
        else:
            direction = -1 if event.delta > 0 else 1
        self.form_canvas.yview_scroll(direction, 'units')

    def _bind_form_scroll(self, widget):
        widget.bind('<MouseWheel>', self._on_wheel)
        widget.bind('<Button-4>', self._on_wheel)
        widget.bind('<Button-5>', self._on_wheel)
        for child in widget.winfo_children():
            self._bind_form_scroll(child)

    def _switch(self, mode):
        self.mode = mode
        self._render()

    def _render(self):
        for child in self.panel.winfo_children():
            child.destroy()
        self.fields = {}
        self._tabs()
        if self.mode == 'login':
            self._heading('Đăng nhập an toàn', 'Chào mừng trở lại',
                          'Sử dụng email đã xác minh hoặc tên đăng nhập của bạn.')
            field = self._field('identifier', 'Email hoặc tên đăng nhập')
            self._field('password', 'Mật khẩu', secret=True)
            self._button('Đăng nhập  →', self._login)
            self._link('Chưa có tài khoản? Đăng ký bằng email', 'register')
            self._link('Quên mật khẩu? Nhận mã OTP', 'forgot')
            self._label(self.panel, '🔒  Mật khẩu được bảo vệ bằng PBKDF2-SHA256.',
                        9, '#8795A4', WHITE).pack(pady=(20, 0))
            self.fields['password'].bind('<Return>', lambda _event: self._login())
        elif self.mode == 'register':
            self._heading('Tạo tài khoản', 'Gia nhập GrandStay',
                          'Xác minh địa chỉ email bằng OTP trước khi tạo tài khoản.')
            field = self._field('name', 'Họ và tên')
            self._field('username', 'Tên đăng nhập (3–60 ký tự)')
            self._field('phone', 'Số điện thoại (bắt buộc, không nhận SMS)')
            self._field('email', 'Email của bạn')
            self._field('password', 'Mật khẩu (ít nhất 8 ký tự)', secret=True)
            self._field('confirmation', 'Nhập lại mật khẩu', secret=True)
            self._field('otp', 'Mã OTP 6 chữ số')
            self._button('Gửi mã OTP đến email', self._send_registration_otp, False)
            self._button('Xác minh và tạo tài khoản  →', self._register)
            self._link('Đã có tài khoản? Đăng nhập', 'login')
        else:
            self._heading('Khôi phục bảo mật', 'Quên mật khẩu?',
                          'Nhập email đã xác minh. Mã OTP có hiệu lực trong 10 phút.')
            field = self._field('email', 'Email đã đăng ký')
            self._field('otp', 'Mã OTP 6 chữ số')
            self._field('password', 'Mật khẩu mới', secret=True)
            self._field('confirmation', 'Nhập lại mật khẩu mới', secret=True)
            self._button('Gửi mã khôi phục', self._send_reset_otp, False)
            self._button('Xác minh và đổi mật khẩu  →', self._reset_password)
            self._link('← Trở lại đăng nhập', 'login')
        self._bind_form_scroll(self.panel)
        self.form_canvas.yview_moveto(0)
        self.panel.update_idletasks()
        self._fit_panel()
        field.focus_set()

    def _value(self, key):
        return self.fields[key].get().strip()

    def _login(self):
        try:
            user = self.c.login(self._value('identifier'), self._value('password'))
            if user.get('requires_password_change'):
                messagebox.showinfo('GrandStay',
                    'Bạn đang dùng mật khẩu tạm được gửi qua Gmail.\n'
                    'Hãy đặt mật khẩu riêng để kích hoạt quyền truy cập.',
                    parent=self.winfo_toplevel())
                while True:
                    values = form_dialog(self, 'BẮT BUỘC đổi mật khẩu lần đầu', [
                        ('old', 'Mật khẩu tạm trong Gmail', '', None, True),
                        ('new', 'Mật khẩu mới (ít nhất 8 ký tự)', '', None, True),
                        ('confirm', 'Nhập lại mật khẩu mới', '', None, True),
                    ])
                    if values is None:
                        self.c.logout()
                        return
                    try:
                        self.c.change_password(values['old'], values['new'], values['confirm'])
                        break
                    except Exception as exc:
                        error(self, exc)
            if user['role'] == 'customer':
                self.app.show_customer()
            else:
                self.app.show_staff()
        except Exception as exc:
            error(self, exc)

    def _send_registration_otp(self):
        try:
            self.c.request_registration_otp(self._value('email'))
            messagebox.showinfo('GrandStay', 'Đã gửi OTP. Kiểm tra hộp thư và cả mục Spam.',
                                parent=self.winfo_toplevel())
        except Exception as exc:
            error(self, exc)

    def _register(self):
        try:
            self.c.register_customer(self._value('username'), self._value('name'),
                                     self._value('email'), self._value('password'),
                                     self._value('confirmation'), self._value('otp'),
                                     self._value('phone'))
            self.c.login(self._value('email'), self._value('password'))
            self.app.show_customer()
        except Exception as exc:
            error(self, exc)

    def _send_reset_otp(self):
        try:
            message = self.c.request_password_reset(self._value('email'))
            messagebox.showinfo('GrandStay', message, parent=self.winfo_toplevel())
        except Exception as exc:
            error(self, exc)

    def _reset_password(self):
        try:
            self.c.reset_password_with_otp(self._value('email'), self._value('otp'),
                                           self._value('password'),
                                           self._value('confirmation'))
            messagebox.showinfo('GrandStay', 'Đã đổi mật khẩu. Hãy đăng nhập lại.',
                                parent=self.winfo_toplevel())
            self._switch('login')
        except Exception as exc:
            error(self, exc)
