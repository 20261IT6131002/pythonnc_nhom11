from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class StaffChatScreenMixin:
    def _chat(self):
        ttk.Label(self.body, text='Chatbot quy tắc: hỏi giá phòng, dịch vụ, phòng trống theo ngày.',
                  font=('Segoe UI', 11)).pack(anchor='w', pady=(0, 13))
        output = tk.Text(self.body, wrap='word', font=('Segoe UI', 11),
                         bg='white', fg='#234661', relief='flat', state='disabled')
        output.pack(fill='both', expand=True)
        bottom = ttk.Frame(self.body)
        bottom.pack(fill='x', pady=(10, 0))
        prompt = tk.StringVar()
        entry = ttk.Entry(bottom, textvariable=prompt)
        entry.pack(side='left', fill='x', expand=True, padx=(0, 9), ipady=6)

        def send():
            value = prompt.get().strip()
            if not value:
                return
            reply = self.c.ask_chatbot(value)
            output.configure(state='normal')
            output.insert('end', 'Bạn: ' + value + '\nGrandStay: ' + reply + '\n\n')
            output.see('end')
            output.configure(state='disabled')
            prompt.set('')

        self._button(bottom, 'Gửi', send, True)
        entry.bind('<Return>', lambda _: self._safe(send))
        entry.focus_set()
