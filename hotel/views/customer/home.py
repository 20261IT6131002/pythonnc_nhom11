from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class CustomerHomeMixin:
    def show_home(self):
        self._clear()
        hero = tk.Frame(self.content, bg=DEEP, height=430)
        hero.pack(fill='x')
        hero.pack_propagate(False)
        left = tk.Frame(hero, bg=DEEP, padx=48)
        left.pack(side='left', fill='both', expand=True)
        text(left, 'GRANDSTAY HOTEL & RESORT', 10, GOLD_LIGHT, DEEP,
             'bold').pack(anchor='w', pady=(52, 25))
        text(left, 'Nơi mỗi kỳ nghỉ', 31, WHITE, DEEP, 'bold').pack(anchor='w')
        tk.Label(left, text='trở nên đáng nhớ.', bg=DEEP, fg=GOLD_LIGHT,
                 font=('Georgia', 31, 'italic')).pack(anchor='w', pady=(0, 19))
        text(left, 'Khám phá không gian nghỉ dưỡng hiện đại, tận hưởng dịch vụ tinh tế '
             'và đặt phòng chỉ trong vài thao tác.', 11, '#bed1de', DEEP,
             wraplength=460, justify='left').pack(anchor='w')
        tk.Button(left, text='Khám phá phòng nghỉ ↗', command=self.show_rooms,
                  bg=GOLD_LIGHT, fg=DEEP, bd=0, relief='flat', cursor='hand2',
                  font=(FONT, 11, 'bold'), padx=18, pady=12).pack(anchor='w', pady=(25, 16))
        text(left, '✦  Dịch vụ chu đáo      ✦  Đặt phòng nhanh chóng',
             9, '#a8c1d3', DEEP).pack(anchor='w')
        illustration = tk.Canvas(hero, width=515, height=340, bg=DEEP,
                                 highlightthickness=0)
        illustration.pack(side='right', padx=(0, 45), pady=45)
        illustration.bind('<Configure>', lambda e: hotel_art(illustration,
                          max(20, e.width), max(20, e.height)))
        hotel_art(illustration, 515, 340)

        search = self._section(25)
        self._search_form(search, include_type=False)
        self._home_types()
        self._service_features()
        cta = tk.Frame(self.content, bg=NAVY, padx=44, pady=35)
        cta.pack(fill='x', padx=42, pady=(20, 40))
        text(cta, 'SẴN SÀNG CHO KỲ NGHỈ?', 9, GOLD_LIGHT, NAVY,
             'bold').pack(anchor='w')
        text(cta, 'Bắt đầu hành trình cùng GrandStay.', 21, WHITE, NAVY,
             'bold').pack(side='left', pady=(8, 0))
        solid_button(cta, 'Đặt phòng ngay →', self.show_rooms, light=True).pack(side='right')
        self._footer()

    def _search_form(self, parent, include_type=True):
        card = tk.Frame(parent, bg=WHITE, highlightbackground=EDGE,
                        highlightthickness=1, padx=20, pady=20)
        card.pack(fill='x')
        fields = [('Ngày nhận phòng', self.start, 20),
                  ('Ngày trả phòng', self.end, 20), ('Số khách', self.guests, 9)]
        for label, variable, width in fields:
            cell = tk.Frame(card, bg=WHITE)
            cell.pack(side='left', fill='x', expand=True, padx=(0, 18))
            text(cell, label, 9, '#4b5c6d', WHITE, 'bold').pack(anchor='w', pady=(0, 8))
            ttk.Entry(cell, textvariable=variable, width=width).pack(fill='x', ipady=7)
        if include_type:
            choices = ['Tất cả'] + [t['name'] for t in self.c.public_types()]
            if self.type_name.get() not in choices:
                self.type_name.set('Tất cả')
            cell = tk.Frame(card, bg=WHITE)
            cell.pack(side='left', fill='x', expand=True, padx=(0, 17))
            text(cell, 'Loại phòng', 9, '#4b5c6d', WHITE, 'bold').pack(anchor='w', pady=(0, 8))
            ttk.Combobox(cell, textvariable=self.type_name, state='readonly',
                         values=choices, width=18).pack(fill='x', ipady=6)
        solid_button(card, 'Tìm phòng trống →', self.show_rooms).pack(side='left', pady=(13, 0))

    def _home_types(self):
        section = self._section()
        text(section, 'TRẢI NGHIỆM ĐẲNG CẤP', 9, '#a68255', WHITE,
             'bold').pack(anchor='w')
        text(section, 'Phòng nghỉ dành cho bạn', 23, NAVY, WHITE,
             'bold').pack(anchor='w', pady=(7, 4))
        text(section, 'Chọn căn phòng phù hợp với nhu cầu và hành trình của bạn.',
             10, MUTED, WHITE).pack(anchor='w', pady=(0, 24))
        cards = tk.Frame(section, bg=WHITE)
        cards.pack(fill='x')
        items = self.c.public_types()[:6]
        for i, item in enumerate(items):
            self._type_card(cards, item, i)
        if not items:
            text(cards, 'Chưa có phòng mẫu; chạy scripts.seed để tạo dữ liệu.',
                 11, MUTED).pack(anchor='w')

    def _type_card(self, parent, item, index):
        card = tk.Frame(parent, bg=WHITE, highlightbackground=EDGE,
                        highlightthickness=1)
        card.grid(row=index // 3, column=index % 3, sticky='nsew', padx=8, pady=8)
        parent.grid_columnconfigure(index % 3, weight=1, uniform='typecards')
        art = tk.Canvas(card, height=150, bg='#b3c7d4', highlightthickness=0)
        art.pack(fill='x')
        art.bind('<Configure>', lambda e: hotel_art(art, e.width, 150, room=True))
        details = tk.Frame(card, bg=WHITE, padx=18, pady=15)
        details.pack(fill='x')
        text(details, f"Tối đa {item['capacity']} khách", 9, GOLD, WHITE,
             'bold').pack(anchor='w')
        text(details, item['name'], 16, NAVY, WHITE, 'bold').pack(anchor='w', pady=(6, 5))
        text(details, item.get('description') or 'Phòng nghỉ tiện nghi với dịch vụ chu đáo.',
             9, MUTED, WHITE, wraplength=290, justify='left').pack(anchor='w')
        text(details, f"Từ {item['price']} / đêm", 12, NAVY, WHITE,
             'bold').pack(anchor='w', pady=(17, 10))
        solid_button(details, 'Xem phòng →', self.show_rooms).pack(anchor='w')

    def _service_features(self):
        section = self._section(bg=BACKGROUND)
        text(section, 'DỊCH VỤ TIỆN ÍCH', 9, '#a68255', BACKGROUND,
             'bold').pack(anchor='w')
        text(section, 'Chăm sóc bạn trong từng chi tiết', 23, NAVY,
             BACKGROUND, 'bold').pack(anchor='w', pady=(8, 22))
        row = tk.Frame(section, bg=BACKGROUND)
        row.pack(fill='x')
        blocks = [('✦', 'Không gian tiện nghi',
                   'Hệ thống phòng với nhiều lựa chọn phù hợp nhu cầu lưu trú.'),
                  ('☕', 'Ẩm thực & dịch vụ',
                   'Thêm các tiện ích ngay trong quá trình lưu trú.'),
                  ('◈', 'Đặt phòng dễ dàng',
                   'Chủ động chọn ngày, tìm phòng trống và tra cứu mã đặt phòng.')]
        for symbol, title, message in blocks:
            card = tk.Frame(row, bg=WHITE, padx=23, pady=22)
            card.pack(side='left', expand=True, fill='both', padx=8)
            text(card, symbol, 24, GOLD, WHITE).pack(anchor='w')
            text(card, title, 13, NAVY, WHITE, 'bold').pack(anchor='w', pady=(8, 7))
            text(card, message, 9, MUTED, WHITE, wraplength=260,
                 justify='left').pack(anchor='w')

    def _footer(self):
        footer = tk.Frame(self.content, bg='#0f273a', padx=42, pady=26)
        footer.pack(fill='x')
        text(footer, 'GrandStay', 19, WHITE, '#0f273a', 'bold').pack(anchor='w')
        text(footer, 'Nâng niu từng khoảnh khắc nghỉ dưỡng của bạn.',
             10, '#a9c0d0', '#0f273a').pack(anchor='w', pady=(4, 0))
        text(footer, '© GrandStay · Dự án học tập Nhóm 11',
             8, '#a9c0d0', '#0f273a').pack(anchor='e')

    def _banner(self, eyebrow, title, description):
        banner = tk.Frame(self.content, bg='#193950', padx=48, pady=30)
        banner.pack(fill='x')
        text(banner, eyebrow, 9, GOLD_LIGHT, '#193950', 'bold').pack(anchor='w')
        text(banner, title, 25, WHITE, '#193950', 'bold').pack(anchor='w', pady=(8, 7))
        text(banner, description, 10, '#bacbd8', '#193950').pack(anchor='w')
