"""Guest/Customer floating chatbot, with a correctly docked send area."""
import tkinter as tk
from hotel.views.components.chat_panel import ChatPanel


class CustomerChatMixin:
    def ask(self):
        chat = tk.Toplevel(self)
        chat.title('GrandStay Assistant · Tư vấn 24/7')
        chat.geometry('570x650')
        chat.minsize(440, 480)
        chat.transient(self.winfo_toplevel())
        role = 'customer' if self.c.user and self.c.user.get('role') == 'customer' else 'guest'
        panel = ChatPanel(chat, self.c, role=role, login_callback=self.app.show_login)
        panel.pack(fill='both', expand=True)
        chat.lift()
        panel.entry.focus_set()
