"""Read models for service orders and promotions."""
from sqlalchemy import select

from hotel.models.entities import Booking, Customer, Promotion, ServiceOrder


class ServiceRepository:
    def __init__(self, db):
        self.db = db

    def orders(self, user, booking_id=None):
        query = select(ServiceOrder, Booking.code, Customer.full_name).join(
            Booking, ServiceOrder.booking_id == Booking.id).join(Customer)
        if user.role == 'customer':
            query = query.where(Customer.user_id == user.id)
        if booking_id is not None:
            query = query.where(ServiceOrder.booking_id == int(booking_id))
        return self.db.execute(query.order_by(ServiceOrder.id.desc()).limit(500)).all()

    def promotions(self):
        return self.db.scalars(select(Promotion).order_by(Promotion.id.desc())).all()
