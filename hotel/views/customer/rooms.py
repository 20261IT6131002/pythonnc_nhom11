from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class CustomerRoomsMixin:
    def show_rooms(self):
        self._clear()
        self._banner('GRANDSTAY COLLECTION', 'Tìm phòng nghỉ phù hợp',
                     'Chọn ngày lưu trú và xem chính xác các phòng còn khả dụng.')
        content = self._section(35)
        self._search_form(content)
        list_area = tk.Frame(content, bg=WHITE)
        list_area.pack(fill='x', pady=(28, 0))
        try:
            type_id = next((t['id'] for t in self.c.public_types()
                            if t['name'] == self.type_name.get()), None)
            rooms = self.c.available(self.start.get(), self.end.get(),
                                     self.guests.get(), room_type_id=type_id)
            text(list_area, 'DANH SÁCH PHÒNG', 9, '#a68255', WHITE,
                 'bold').pack(anchor='w')
            text(list_area, f'{len(rooms)} phòng phù hợp', 23, NAVY, WHITE,
                 'bold').pack(anchor='w', pady=(7, 20))
            cards = tk.Frame(list_area, bg=WHITE)
            cards.pack(fill='x')
            if not rooms:
                empty = tk.Frame(cards, bg=BACKGROUND, padx=30, pady=45)
                empty.pack(fill='x')
                text(empty, 'Không tìm thấy phòng phù hợp. Hãy đổi ngày hoặc số khách.',
                     11, MUTED, BACKGROUND).pack()
            for i, room in enumerate(rooms):
                self._room_card(cards, room, i)
        except Exception as exc:
            error(self, exc)
        self._footer()

    def _room_card(self, parent, room, index):
        card = tk.Frame(parent, bg=WHITE, highlightbackground=EDGE, highlightthickness=1)
        card.grid(row=index // 3, column=index % 3, sticky='nsew', padx=8, pady=8)
        parent.grid_columnconfigure(index % 3, weight=1, uniform='roomcards')
        art = tk.Canvas(card, height=170, bg='#b3c7d4', highlightthickness=0)
        art.pack(fill='x')
        art.bind('<Configure>', lambda e: hotel_art(art, e.width, 170, room=True))
        details = tk.Frame(card, bg=WHITE, padx=18, pady=16)
        details.pack(fill='x')
        text(details, f"Tầng {room['floor']} · Tối đa {room['capacity']} khách",
             9, GOLD, WHITE, 'bold').pack(anchor='w')
        text(details, f"{room['type']} · {room['number']}", 15, NAVY,
             WHITE, 'bold').pack(anchor='w', pady=(6, 7))
        text(details, room['description'] or 'Không gian hiện đại, tiện nghi.',
             9, MUTED, WHITE, wraplength=280, justify='left').pack(anchor='w')
        price = tk.Frame(details, bg=WHITE)
        price.pack(fill='x', pady=(18, 0))
        text(price, room['price'] + ' / đêm', 12, NAVY, WHITE,
             'bold').pack(side='left')
        solid_button(details, 'Đặt phòng →',
                     lambda room_id=room['id']: self.book_room(room_id)).pack(
                         anchor='e', pady=(10, 0))

    def book_room(self, room_id):
        account = self.c.user if self.c.user and self.c.user['role'] == 'customer' else None
        fields = [('name', 'Họ và tên', account['name'] if account else ''),
                  ('phone', 'Số điện thoại', account.get('phone', '') if account else ''),
                  ('email', 'Email' if account else 'Gmail để nhận OTP xác minh đơn',
                   account.get('email', '') if account else ''),
                  ('guests', 'Số khách', self.guests.get()),
                  ('checkin', 'Ngày nhận (YYYY-MM-DD)', self.start.get()),
                  ('checkout', 'Ngày trả (YYYY-MM-DD)', self.end.get()),
                  ('notes', 'Ghi chú', '')]
        value = form_dialog(self, 'Đặt phòng GrandStay', fields)
        if value is None:
            return
        try:
            value['room_id'] = room_id
            if not account:
                self.c.request_guest_booking_otp(value['email'])
                otp_values = form_dialog(self, 'Xác minh email trước khi đặt phòng', [
                    ('otp', 'Mã OTP 6 chữ số gửi tới Gmail', ''),
                ])
                if otp_values is None:
                    return
                value['guest_otp'] = otp_values['otp']
            code = self.c.book(value)
            success(self, f'Đã tiếp nhận yêu cầu đặt phòng!\n\nMã đặt phòng: {code}\n'
                          'Lưu mã này và số điện thoại để tra cứu. Lễ tân sẽ xác nhận yêu cầu.')
            self.show_rooms()
        except Exception as exc:
            error(self, exc)
