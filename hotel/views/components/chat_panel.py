"""Reusable GrandStay chat UI for Customer / Receptionist / Admin.

The composer is packed at the bottom *before* the expanding transcript so the
Entry/Send controls never disappear in smaller Tkinter windows. Network calls
run on a worker thread and all Tk calls stay on the Tk event-loop thread.
"""
from __future__ import annotations

import queue
import threading
from datetime import date, timedelta
import tkinter as tk
from tkinter import ttk, simpledialog


NAVY = '#18354e'
BACKGROUND = '#f4f7fb'
WHITE = '#ffffff'
ACCENT = '#0b78c9'
MUTED = '#71859a'


EXAMPLES = {
    'guest': ['Giá phòng Deluxe bao nhiêu?', 'Bạn có dịch vụ gì?',
              'Tìm phòng trống theo ngày'],
    'customer': ['Đặt phòng của tôi', 'Có những loại phòng nào?',
                 'Tìm phòng trống theo ngày'],
    'receptionist': ['Khách nhận phòng hôm nay', 'Đơn chờ xác nhận',
                     'Tìm phòng trống theo ngày'],
    'admin': ['Doanh thu 30 ngày gần đây', 'Tỷ lệ phòng đang có khách hôm nay',
              'Dịch vụ có giá trị phát sinh cao nhất'],
}


class ChatPanel(tk.Frame):
    def __init__(self, parent, controller, role='guest', login_callback=None, **kwargs):
        super().__init__(parent, bg=BACKGROUND, **kwargs)
        self.controller, self.role = controller, role
        self.login_callback = login_callback
        self.session_id = None
        self.pending = None
        self._busy = False
        self._results = queue.Queue()
        self._build()
        self.after(120, self._poll)
        if self.role == 'customer' and getattr(self.controller, '_chat_booking_handoff', None):
            self.after(250, self._resume_after_login)

    def _build(self):
        captions = {
            'guest': 'Trợ lý tư vấn phòng và dịch vụ GrandStay',
            'customer': 'Tư vấn, tìm phòng, đặt phòng, tra cứu đơn của bạn',
            'receptionist': 'Trợ lý nghiệp vụ lễ tân • Tra cứu có phân quyền',
            'admin': 'Trợ lý quản trị • Báo cáo từ dữ liệu MySQL',
        }
        header = tk.Frame(self, bg=NAVY, padx=16, pady=12)
        header.pack(side='top', fill='x')
        tk.Label(header, text='✦ GrandStay Assistant', bg=NAVY, fg=WHITE,
                 font=('Segoe UI', 15, 'bold')).pack(anchor='w')
        tk.Label(header, text=captions.get(self.role, captions['guest']), bg=NAVY,
                 fg='#c8dae8', font=('Segoe UI', 10)).pack(anchor='w', pady=(3, 0))

        # Pack bottom controls BEFORE the expanding transcript to prevent them
        # being cropped by Tk's geometry manager in small container windows.
        bottom = tk.Frame(self, bg=WHITE, padx=12, pady=10)
        bottom.pack(side='bottom', fill='x')
        self.confirm_frame = tk.Frame(bottom, bg=WHITE)
        self.confirm_frame.pack(fill='x')
        prompt_bar = tk.Frame(bottom, bg=WHITE)
        prompt_bar.pack(fill='x')
        self.entry = tk.Entry(prompt_bar, font=('Segoe UI', 11), bg=BACKGROUND,
                              fg=NAVY, relief='solid', bd=1)
        self.entry.pack(side='left', fill='x', expand=True, ipady=8, padx=(0, 8))
        self.entry.bind('<Return>', self._return_key)
        self.send_button = tk.Button(prompt_bar, text='Gửi', command=self.send,
                                     bg=ACCENT, fg=WHITE, activebackground='#08629f',
                                     activeforeground=WHITE, bd=0, padx=22, pady=9,
                                     font=('Segoe UI', 10, 'bold'), cursor='hand2')
        self.send_button.pack(side='right')
        tk.Label(bottom, text='Dữ liệu phòng và giao dịch lấy từ MySQL • AI không tự thực hiện thanh toán',
                 bg=WHITE, fg=MUTED, font=('Segoe UI', 8),
                 anchor='w').pack(fill='x', pady=(8, 0))
        quick = tk.Frame(self, bg=BACKGROUND, padx=10, pady=7)
        quick.pack(side='top', fill='x')
        tk.Button(quick, text='Lịch sử', command=self.show_history,
                  bg=WHITE, fg=NAVY, relief='groove', bd=1, cursor='hand2').pack(side='right', padx=(5, 0))
        tk.Button(quick, text='Chat mới', command=self.new_chat,
                  bg=WHITE, fg=NAVY, relief='groove', bd=1, cursor='hand2').pack(side='right')
        tk.Label(quick, text='Gợi ý:', bg=BACKGROUND, fg=MUTED,
                 font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))
        for text in EXAMPLES.get(self.role, [])[:2]:
            shown = text if len(text) < 34 else text[:31] + '…'
            tk.Button(quick, text=shown, command=lambda value=text: self._preset(value),
                      bg=WHITE, fg=NAVY, relief='groove', bd=1, cursor='hand2',
                      font=('Segoe UI', 9)).pack(side='left', padx=3)
        transcript = tk.Frame(self, bg=BACKGROUND)
        transcript.pack(side='top', fill='both', expand=True, padx=10, pady=7)
        scroll = ttk.Scrollbar(transcript, orient='vertical')
        scroll.pack(side='right', fill='y')
        self.output = tk.Text(transcript, wrap='word', bg=WHITE, fg=NAVY,
                              font=('Segoe UI', 11), padx=15, pady=14,
                              relief='flat', bd=0, state='disabled',
                              yscrollcommand=scroll.set)
        self.output.pack(side='left', fill='both', expand=True)
        scroll.configure(command=self.output.yview)
        self.output.tag_configure('person', foreground='#0c6da8', spacing1=13,
                                  font=('Segoe UI', 10, 'bold'))
        self.output.tag_configure('bot', foreground=NAVY, spacing1=13,
                                  font=('Segoe UI', 10, 'bold'))
        self.output.tag_configure('body', foreground='#344b60', spacing3=6)
        self._append('bot', 'Xin chào! Hãy hỏi tôi bằng tiếng Việt. Tôi sẽ kiểm tra dữ liệu khách sạn thật khi cần.')

    def _preset(self, value):
        if self._busy:
            return
        self.entry.delete(0, 'end')
        self.entry.insert(0, value)
        self.entry.focus_set()

    def _append(self, sender, message):
        if not self.winfo_exists():
            return
        self.output.configure(state='normal')
        self.output.insert('end', ('Bạn' if sender == 'person' else 'GrandStay') + '\n', sender)
        self.output.insert('end', str(message) + '\n\n', 'body')
        self.output.configure(state='disabled')
        self.output.see('end')

    def _return_key(self, _event):
        self.send()
        return 'break'

    def _set_busy(self, busy):
        self._busy = busy
        self.send_button.configure(state='disabled' if busy else 'normal',
                                   text='Đang xử lý...' if busy else 'Gửi')
        self.entry.configure(state='disabled' if busy else 'normal')

    def _run(self, method, *args):
        def worker():
            try:
                result = method(*args)
                self._results.put((True, result))
            except Exception as exc:
                self._results.put((False, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def send(self):
        if self._busy:
            return
        msg = self.entry.get().strip()
        if not msg:
            return
        self.entry.delete(0, 'end')
        self._append('person', msg)
        self._set_busy(True)
        self._run(self.controller.chat_send, msg, self.session_id)

    def _poll(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                ok, result = self._results.get_nowait()
                self._set_busy(False)
                if ok:
                    if result is None:
                        continue
                    self.session_id = result.get('session_id', self.session_id)
                    self._append('bot', result.get('reply', ''))
                    self.pending = result.get('confirmation')
                    if result.get('login_required') and self.role == 'guest':
                        self.pending = {'login_required': True, 'label': 'Đăng nhập / Đăng ký'}
                    if self.pending and self.pending.get('otp_required') and 'Đã gửi mã OTP' in result.get('reply',''):
                        self.pending['otp_sent'] = True
                    self._show_confirmation()
                else:
                    self._append('bot', 'Không thể thực hiện yêu cầu: ' + result)
                self.entry.focus_set()
        except queue.Empty:
            pass
        self.after(120, self._poll)

    def _show_confirmation(self):
        for child in self.confirm_frame.winfo_children():
            child.destroy()
        if not self.pending:
            return
        if self.pending.get('login_required'):
            tk.Label(self.confirm_frame, text='Cần đăng nhập/đăng ký trước khi đặt phòng:',
                     bg=WHITE, fg=NAVY, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(3, 5))
            tk.Button(self.confirm_frame, text='Đăng nhập / Đăng ký',
                      command=self._go_login, bg='#147b55', fg=WHITE, bd=0,
                      padx=12, pady=6, cursor='hand2').pack(side='left')
            return
        tk.Label(self.confirm_frame, text='Chỉ tạo đơn sau khi bạn chủ động xác nhận:',
                 bg=WHITE, fg=NAVY, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(3, 5))
        tk.Button(self.confirm_frame, text=('Gửi mã OTP' if self.pending.get('otp_required') and not self.pending.get('otp_sent') else '✓ Xác nhận đặt phòng'),
                  command=self.confirm, bg='#147b55', fg=WHITE, bd=0, padx=12, pady=6,
                  cursor='hand2').pack(side='left', padx=(0, 8))
        tk.Button(self.confirm_frame, text='Hủy yêu cầu', command=self.cancel,
                  bg='#f4f6f8', fg=NAVY, bd=1, padx=12, pady=6,
                  cursor='hand2').pack(side='left')

    def _go_login(self):
        if self._busy or not self.login_callback:
            self._append('bot', 'Vui lòng chuyển đến trang Đăng nhập / Đăng ký.')
            return
        self.winfo_toplevel().destroy()
        self.login_callback()

    def _resume_after_login(self):
        if self._busy or not self.winfo_exists():
            return
        if getattr(self.controller, '_chat_booking_handoff', None):
            self._append('bot', 'Đã đăng nhập. Đang kiểm tra lại phòng đã chọn trên MySQL...')
            self._set_busy(True)
            self._run(self.controller.chat_resume_booking)

    def confirm(self):
        if self._busy or not self.pending:
            return
        if self.pending.get('login_required'):
            self._go_login()
            return
        token = self.pending['token']
        if self.pending.get('otp_required') and not self.pending.get('otp_sent'):
            self._set_busy(True)
            self._run(self.controller.chat_request_otp, self.session_id, token)
            # The response tells _poll that OTP has been sent.
            return
        otp = None
        if self.pending.get('otp_required'):
            otp = simpledialog.askstring('Xác thực email', 'Nhập mã OTP 6 số đã nhận qua email:',
                                         parent=self, show='*')
            if otp is None:
                return
        self._set_busy(True)
        self.pending = None
        self._show_confirmation()
        self._run(self.controller.chat_confirm, self.session_id, token, otp)

    def cancel(self):
        if self._busy or not self.pending:
            return
        if self.pending.get('login_required'):
            self.pending = None
            self.controller._chat_booking_handoff = None
            self._show_confirmation()
            self._append('bot', 'Đã hủy yêu cầu. Chưa tạo đặt phòng.')
            return
        token = self.pending['token']
        self._set_busy(True)
        self.pending = None
        self._show_confirmation()
        self._run(self.controller.chat_cancel, self.session_id, token)

    def show_history(self):
        if self._busy:
            return
        if self.role == 'guest':
            self._append('bot', 'Hãy đăng nhập để xem các cuộc trò chuyện trước đây.')
            return
        try:
            sessions = self.controller.chat_sessions()
        except Exception as exc:
            self._append('bot', 'Không tải được lịch sử: ' + str(exc))
            return
        if not sessions:
            self._append('bot', 'Chưa có lịch sử trò chuyện nào.')
            return
        popup = tk.Toplevel(self)
        popup.title('Lịch sử Chat – GrandStay')
        popup.geometry('370x390')
        popup.transient(self.winfo_toplevel())
        tk.Label(popup, text='Chọn một cuộc trò chuyện để mở lại',
                 font=('Segoe UI', 11, 'bold')).pack(pady=(13, 8))
        listbox = tk.Listbox(popup, font=('Segoe UI', 10))
        listbox.pack(fill='both', expand=True, padx=12, pady=7)
        for item in sessions:
            listbox.insert('end', item['when'])

        def choose():
            sel = listbox.curselection()
            if not sel:
                return
            selected = sessions[sel[0]]['session_id']
            try:
                messages = self.controller.chat_history(selected)
            except Exception as exc:
                self._append('bot', 'Không mở được lịch sử: ' + str(exc))
                return
            self.session_id = selected
            self.pending = None
            self._show_confirmation()
            self.output.configure(state='normal')
            self.output.delete('1.0', 'end')
            self.output.configure(state='disabled')
            for msg in messages:
                self._append('person' if msg['sender'] == 'user' else 'bot', msg['content'])
            popup.destroy()

        tk.Button(popup, text='Mở cuộc trò chuyện', command=choose,
                  bg=ACCENT, fg=WHITE, padx=13, pady=7).pack(pady=(0, 10))

    def new_chat(self):
        if self._busy:
            return
        if hasattr(self.controller, '_chat_booking_handoff'):
            self.controller._chat_booking_handoff = None
        self.session_id = None
        self.pending = None
        self._show_confirmation()
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        self.output.configure(state='disabled')
        self._append('bot', 'Đã mở cuộc trò chuyện mới. Bạn cần hỗ trợ gì?')
        self.entry.focus_set()
