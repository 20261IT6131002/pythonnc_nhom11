"""Thanh menu trái dùng chung cho trang quản trị và lễ tân."""
import tkinter as tk

from hotel.views.components.theme import (
    FONT, SIDEBAR, SIDEBAR_HOVER, WHITE, brand,
)


NAV_GROUPS = [
    ('TỔNG QUAN', [('dashboard', '◫   Dashboard')]),
    ('NGHIỆP VỤ', [('bookings', '▦   Đặt phòng'), ('rooms', '▤   Quản lý phòng'),
                  ('calendar', '▦   Lịch phòng'), ('types', '◇   Loại phòng & giá'),
                  ('customers', '♙   Hồ sơ khách hàng'), ('staying', '♙   Khách đang lưu trú'),
                  ('services', '✦   Dịch vụ'), ('service_orders', '☑   Yêu cầu dịch vụ'),
                  ('promotions', '◇   Khuyến mãi'),
                  ('invoices', '▣   Hóa đơn & thanh toán')]),
    ('QUẢN TRỊ', [('reports', '◴   Báo cáo doanh thu'), ('users', '♧   Tài khoản'),
                 ('links', '☑   Duyệt lịch sử khách'),
                 ('logs', '≡   Nhật ký thao tác'), ('settings', '⚙   Cấu hình khách sạn')]),
    ('KHÁC', [('chat', '✦   Tư vấn tự động')]),
]


def build_sidebar(view, app, allowed_tabs):
    """Sidebar có vùng menu cuộn, phù hợp cả màn hình laptop thấp."""
    left = tk.Frame(view, bg=SIDEBAR, width=252)
    left.pack(side='left', fill='y')
    left.pack_propagate(False)
    logo = brand(left, on_dark=True)
    logo.pack(anchor='w', padx=20, pady=(18, 16))
    tk.Frame(left, bg='#3c5970', height=1).pack(fill='x', padx=16, pady=(0, 8))
    buttons = {}

    # Admin must always see the employee management action even if the lower
    # navigation groups are below the visible edge of the window.
    if 'users' in allowed_tabs:
        tk.Label(left, text='QUẢN TRỊ NHANH', fg='#a8bfce', bg=SIDEBAR,
                 font=(FONT, 9, 'bold'), anchor='w').pack(
                     fill='x', padx=24, pady=(7, 5))
        employee_button = tk.Button(
            left, text='♧   Tài khoản',
            font=(FONT, 10, 'bold'), bg=SIDEBAR, fg='#e8c28f',
            activebackground=SIDEBAR_HOVER, activeforeground=WHITE,
            relief='flat', bd=0, anchor='w', cursor='hand2',
            padx=19, pady=11, command=lambda: view._on_nav('users'))
        employee_button.pack(fill='x', padx=10, pady=(0, 8))
        buttons['users'] = employee_button

    # Keep the brand, employee shortcut and footer fixed; only the navigation
    # groups scroll. A Scrollbar is also visible for touchpad users.
    footer = tk.Frame(left, bg=SIDEBAR)
    footer.pack(side='bottom', fill='x', pady=(5, 10))
    tk.Frame(footer, bg='#3c5970', height=1).pack(fill='x', padx=16, pady=(0, 6))
    tk.Button(footer, text='↗   Trang khách hàng', command=app.show_guest,
              bg=SIDEBAR, fg='#c3d4e2', activebackground=SIDEBAR_HOVER,
              activeforeground=WHITE, relief='flat', bd=0, cursor='hand2',
              font=(FONT, 10, 'bold'), anchor='w', padx=19, pady=9).pack(
                  fill='x', padx=10)

    viewport = tk.Frame(left, bg=SIDEBAR)
    viewport.pack(fill='both', expand=True)
    scrollbar = tk.Scrollbar(viewport, orient='vertical', width=11,
                             bg=SIDEBAR_HOVER, troughcolor=SIDEBAR,
                             activebackground='#57748a', relief='flat', bd=0)
    scrollbar.pack(side='right', fill='y')
    canvas = tk.Canvas(viewport, bg=SIDEBAR, highlightthickness=0,
                       borderwidth=0, yscrollcommand=scrollbar.set)
    canvas.pack(side='left', fill='both', expand=True)
    scrollbar.configure(command=canvas.yview)
    content = tk.Frame(canvas, bg=SIDEBAR)
    window = canvas.create_window((0, 0), window=content, anchor='nw')
    content.bind('<Configure>', lambda _event: canvas.configure(
        scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>', lambda event: canvas.itemconfigure(
        window, width=event.width))

    for heading, entries in NAV_GROUPS:
        entries = [(key, label) for key, label in entries
                   if key in allowed_tabs and key != 'users']
        if not entries:
            continue
        tk.Label(content, text=heading, fg='#7e9db6', bg=SIDEBAR,
                 font=(FONT, 9, 'bold'), anchor='w').pack(fill='x', padx=25,
                                                         pady=(12, 5))
        for key, label in entries:
            button = tk.Button(content, text=label, font=(FONT, 10, 'bold'),
                               bg=SIDEBAR, fg='#c3d4e2', activebackground=SIDEBAR_HOVER,
                               activeforeground=WHITE, relief='flat', bd=0, anchor='w',
                               cursor='hand2', padx=19, pady=8,
                               command=lambda tab=key: view._on_nav(tab))
            button.pack(fill='x', padx=10, pady=1)
            buttons[key] = button

    def scroll_menu(event):
        if getattr(event, 'num', None) in (4, 5):
            amount = -2 if event.num == 4 else 2
        else:
            delta = getattr(event, 'delta', 0)
            amount = -2 if delta > 0 else 2
        canvas.yview_scroll(amount, 'units')

    def bind_wheel(widget):
        widget.bind('<MouseWheel>', scroll_menu)
        widget.bind('<Button-4>', scroll_menu)
        widget.bind('<Button-5>', scroll_menu)
        for child in widget.winfo_children():
            bind_wheel(child)

    bind_wheel(canvas)
    return buttons
