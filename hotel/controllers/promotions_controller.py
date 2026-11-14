"""Promotion management and redemption through the existing Controller facade."""
from datetime import date

from hotel.controllers.utils import vnd
from hotel.repositories.services import ServiceRepository
from hotel.services import promotions


class PromotionsControllerMixin:
    def promotions(self, public=False):
        with self._session() as db:
            if not public:
                self._require_staff(db)
            today = date.today()
            return [{'id': row.id, 'code': row.code, 'name': row.name,
                     'discount_type': row.discount_type, 'value': str(row.value),
                     'minimum_amount': str(row.minimum_amount),
                     'starts_on': str(row.starts_on), 'ends_on': str(row.ends_on),
                     'usage_limit': row.usage_limit, 'used_count': row.used_count,
                     'active': row.active}
                    for row in ServiceRepository(db).promotions()
                    if not public or (row.active and row.starts_on <= today <= row.ends_on
                                      and row.used_count < row.usage_limit)]

    def save_promotion(self, values, row_id=None):
        with self._session(read_committed=True) as db:
            actor = self._require_staff(db, admin=True)
            return promotions.save_promotion(db, actor, values, row_id)

    def apply_promotion(self, booking_id, code):
        with self._session(read_committed=True) as db:
            actor = self._require_user(db)
            return vnd(promotions.redeem(db, booking_id, code, actor.id))
