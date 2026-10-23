from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


def form_dialog(parent, title, fields):
    """fields: (key, label, initial, choices or None, secret optional)."""
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent.winfo_toplevel())
    dialog.resizable(False, False)
    dialog.configure(background='#f5f8fb')
    panel = ttk.Frame(dialog, padding=22)
    panel.pack(fill='both', expand=True)
    ttk.Label(panel, text=title, style='FormTitle.TLabel').grid(
        row=0, column=0, columnspan=2, pady=(0, 16), sticky='w')
    vars_ = {}
    first = None
    for i, field in enumerate(fields, 1):
        key, label, default = field[:3]
        choices = field[3] if len(field) > 3 else None
        secret = field[4] if len(field) > 4 else False
        ttk.Label(panel, text=label).grid(row=i, column=0, sticky='w', padx=(0, 12), pady=6)
        v = tk.StringVar(value=str(default))
        vars_[key] = v
        if choices is not None:
            widget = ttk.Combobox(panel, textvariable=v, values=choices,
                                  state='readonly', width=35)
        else:
            widget = ttk.Entry(panel, textvariable=v, show='•' if secret else '', width=38)
        widget.grid(row=i, column=1, sticky='ew', pady=6)
        first = first or widget
    dialog.result = None

    def submit(event=None):
        dialog.result = {key: var.get().strip() for key, var in vars_.items()}
        dialog.destroy()

    def cancel(event=None):
        dialog.destroy()

    bar = ttk.Frame(panel)
    bar.grid(row=len(fields) + 1, column=0, columnspan=2, pady=(16, 0), sticky='e')
    ttk.Button(bar, text='Hủy', command=cancel).pack(side='left', padx=6)
    ttk.Button(bar, text='Lưu', command=submit, style='Accent.TButton').pack(side='left')
    dialog.bind('<Return>', submit)
    dialog.bind('<Escape>', cancel)
    dialog.protocol('WM_DELETE_WINDOW', cancel)
    dialog.update_idletasks()
    root = parent.winfo_toplevel()
    x = root.winfo_rootx() + max(0, (root.winfo_width() - dialog.winfo_width()) // 2)
    y = root.winfo_rooty() + max(0, (root.winfo_height() - dialog.winfo_height()) // 2)
    dialog.geometry(f'+{x}+{y}')
    dialog.grab_set()
    if first:
        first.focus_set()
    dialog.wait_window()
    return dialog.result


def add_tree(parent, columns, rows, height=17, row_key='id'):
    """columns: sequence (field, title, width). Creates a scrollable Treeview."""
    wrapper = ttk.Frame(parent)
    wrapper.pack(fill='both', expand=True, pady=(10, 0))
    tree = ttk.Treeview(wrapper, columns=[c[0] for c in columns], show='headings', height=height)
    xscroll = ttk.Scrollbar(wrapper, orient='horizontal', command=tree.xview)
    yscroll = ttk.Scrollbar(wrapper, orient='vertical', command=tree.yview)
    tree.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
    tree.grid(row=0, column=0, sticky='nsew')
    yscroll.grid(row=0, column=1, sticky='ns')
    xscroll.grid(row=1, column=0, sticky='ew')
    wrapper.columnconfigure(0, weight=1)
    wrapper.rowconfigure(0, weight=1)
    for key, label, width in columns:
        tree.heading(key, text=label)
        tree.column(key, width=width, minwidth=min(width, 80), stretch=False, anchor='w')
    for index, row in enumerate(rows):
        iid = str(row.get(row_key, index))
        status = row.get('status')
        tag = status if status in {'pending', 'confirmed', 'checked_in', 'checked_out',
                                   'cancelled'} else ('alt' if index % 2 else 'normal')
        tree.insert('', 'end', iid=iid, values=[pretty(row.get(c[0], '')) for c in columns],
                    tags=(tag,))
    tree.tag_configure('alt', background='#edf4fb')
    tree.tag_configure('pending', background='#fff8e9')
    tree.tag_configure('confirmed', background='#eaf7ed')
    tree.tag_configure('checked_in', background='#eaf1fc')
    tree.tag_configure('checked_out', background='#ecf8f0')
    tree.tag_configure('cancelled', background='#f9ebed')
    return tree


def pretty(value):
    labels = {'pending': 'Chờ xác nhận', 'confirmed': 'Đã xác nhận',
              'checked_in': 'Đang ở', 'checked_out': 'Đã trả phòng',
              'cancelled': 'Đã hủy'}
    if isinstance(value, str) and value in labels:
        return labels[value]
    if value is True:
        return 'Hoạt động'
    if value is False:
        return 'Ngừng'
    if value is None:
        return ''
    return str(value)


def choice_id(value):
    try:
        return int(str(value).split(' - ', 1)[0].strip())
    except ValueError as exc:
        raise ValueError('Vui lòng chọn một mục trong danh sách.') from exc


def success(parent, text='Thao tác thành công.'):
    messagebox.showinfo('GrandStay', text, parent=parent.winfo_toplevel())


def error(parent, exc):
    messagebox.showerror('GrandStay - Thông báo', str(exc), parent=parent.winfo_toplevel())
