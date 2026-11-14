"""Promotion forms call only the public Controller facade."""
from datetime import date, timedelta

from hotel.views.components.widget_helpers import form_dialog


class PromotionsScreenMixin:
    def _edit_promotion(self, edit=False):
        row = self._chosen() if edit else {}
        labels = ['Phần trăm', 'Số tiền cố định']
        values = form_dialog(self, 'Chương trình khuyến mãi', [
            ('code', 'Mã khuyến mãi', row.get('code', '')),
            ('name', 'Tên chương trình', row.get('name', '')),
            ('discount_type', 'Cách giảm tiền phòng', labels[1] if row.get('discount_type') == 'fixed' else labels[0], labels),
            ('value', 'Mức giảm (% hoặc VND)', row.get('value', '10')),
            ('minimum_amount', 'Tiền phòng tối thiểu (VND)', row.get('minimum_amount', '0')),
            ('starts_on', 'Từ ngày (YYYY-MM-DD)', row.get('starts_on', str(date.today()))),
            ('ends_on', 'Đến ngày (YYYY-MM-DD)', row.get('ends_on', str(date.today() + timedelta(days=30)))),
            ('usage_limit', 'Số lượt sử dụng tối đa', row.get('usage_limit', 100)),
            ('active', 'Đang áp dụng', 'Có' if row.get('active', True) else 'Không', ['Có', 'Không']),
        ])
        if values is not None:
            values['discount_type'] = 'fixed' if values['discount_type'] == labels[1] else 'percent'
            values['active'] = values['active'] == 'Có'
            self.c.save_promotion(values, row.get('id'))
            self._done()

    def _apply_promotion(self):
        row = self._chosen()
        values = form_dialog(self, 'Áp dụng khuyến mãi', [
            ('code', f"Mã giảm tiền phòng cho {row['code']}", ''),
        ])
        if values is not None:
            amount = self.c.apply_promotion(row['id'], values['code'])
            self._done(f'Đã áp dụng giảm {amount} vào tiền phòng; hóa đơn sẽ sử dụng mức giảm này.')
