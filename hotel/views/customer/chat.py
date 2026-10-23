from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class CustomerChatMixin:
    def ask(self):
        chat = tk.Toplevel(self)
        chat.title('GrandStay Assistant · Tư vấn 24/7')
        chat.geometry('400x470')
        chat.transient(self.winfo_toplevel())
        chat.configure(bg=WHITE)
        head = tk.Frame(chat, bg=NAVY, padx=16, pady=12)
        head.pack(fill='x')
        text(head, 'GrandStay Assistant', 13, WHITE, NAVY, 'bold').pack(anchor='w')
        text(head, 'Tư vấn tự động từ dữ liệu khách sạn', 9, '#c9dbe8', NAVY).pack(anchor='w')
        log = tk.Text(chat, wrap='word', bg='#f6f9fc', fg=INK, font=(FONT, 10),
                      relief='flat', state='normal', padx=13, pady=13)
        log.pack(fill='both', expand=True)
        log.insert('end', 'GrandStay: Xin chào! Bạn muốn hỏi giá phòng, dịch vụ '
                          'hay kiểm tra phòng trống theo ngày?\n\n')
        log.configure(state='disabled')
        row = tk.Frame(chat, bg=WHITE, padx=9, pady=9)
        row.pack(fill='x')
        message = tk.StringVar()
        entry = ttk.Entry(row, textvariable=message)
        entry.pack(side='left', fill='x', expand=True, padx=(0, 7), ipady=6)

        def send():
            question = message.get().strip()
            if not question:
                return
            try:
                reply = self.c.ask_chatbot(question)
                log.configure(state='normal')
                log.insert('end', 'Bạn: ' + question + '\nGrandStay: ' + reply + '\n\n')
                log.see('end')
                log.configure(state='disabled')
                message.set('')
            except Exception as exc:
                error(self, exc)

        solid_button(row, 'Gửi', send).pack(side='right')
        entry.bind('<Return>', lambda _: send())
        entry.focus_set()
