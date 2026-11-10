"""Full-width Admin/Receptionist chatbot with role-aware suggestions."""
from hotel.views.components.chat_panel import ChatPanel


class StaffChatScreenMixin:
    def _chat(self):
        role = 'admin' if self.admin else 'receptionist'
        panel = ChatPanel(self.body, self.c, role=role)
        panel.pack(fill='both', expand=True)
