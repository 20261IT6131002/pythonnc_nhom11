from __future__ import annotations
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, filedialog
from hotel.views.components.theme import (BACKGROUND, DEEP, EDGE, FONT, GOLD, GOLD_LIGHT, INK, MUTED, NAVY, SIDEBAR, SIDEBAR_HOVER, WHITE, brand, hotel_art, solid_button, text)
from hotel.views.components.widget_helpers import (add_tree, choice_id, error, form_dialog, success)


class RoomsScreenMixin:
    def _type_options(self):
        return [text for _, text in self.c.choices('types')]

    def _edit_type(self, edit):
        row = self._chosen() if edit else {}
        fields = [] if edit else [('name', 'Tên loại phòng', '')]
        fields += [('capacity', 'Sức chứa', row.get('capacity', 2)),
                   ('price', 'Giá một đêm (VND)', row.get('price', '350000')),
                   ('description', 'Mô tả', row.get('description', ''))]
        values = form_dialog(self, 'Sửa loại phòng' if edit else 'Thêm loại phòng', fields)
        if values is not None:
            self.c.save_type(values, row.get('id'))
            self._done()

    def _edit_room(self, edit):
        row = self._chosen() if edit else {}
        choices = self._type_options()
        default = next((v for v in choices if v.startswith(str(row.get('type_id')) + ' - ')),
                       choices[0] if choices else '')
        fields = [] if edit else [('number', 'Số phòng', '')]
        fields += [('type_id', 'Loại phòng', default, choices),
                   ('floor', 'Tầng', row.get('floor', 1))]
        values = form_dialog(self, 'Sửa phòng' if edit else 'Thêm phòng', fields)
        if values is not None:
            values['type_id'] = choice_id(values['type_id'])
            self.c.save_room(values, row.get('id'))
            self._done()
