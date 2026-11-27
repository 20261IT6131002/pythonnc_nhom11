"""Read models for service orders and promotions."""
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from hotel.models.entities import Booking, Customer, Promotion, Room, ServiceOrder, ServiceUsage


class ServiceRepository:
    def __init__(self, db):
        self.db = db

    def orders(self, user, booking_id=None, *, query='', status='', created_from=None, created_until=None):
        statement = select(ServiceOrder, Booking.code, Customer.full_name, Room.number).join(
            Booking, ServiceOrder.booking_id == Booking.id).join(Customer).join(Room)
        if user.role == 'customer':
            statement = statement.where(Customer.user_id == user.id)
        if booking_id is not None:
            statement = statement.where(ServiceOrder.booking_id == int(booking_id))
        if query:
            statement = statement.where(or_(
                Booking.code.icontains(query, autoescape=True),
                Room.number.icontains(query, autoescape=True),
                Customer.full_name.icontains(query, autoescape=True),
                Customer.phone.contains(query, autoescape=True),
                ServiceOrder.service_name.icontains(query, autoescape=True)))
        if status:
            statement = statement.where(ServiceOrder.status == status)
        if created_from is not None:
            statement = statement.where(ServiceOrder.created_at >= created_from)
        if created_until is not None:
            statement = statement.where(ServiceOrder.created_at <= created_until)
        return self.db.execute(statement.order_by(ServiceOrder.id.desc()).limit(500)).all()

    def booking_orders(self, booking_id):
        return self.db.scalars(select(ServiceOrder).where(ServiceOrder.booking_id == booking_id)
                               .order_by(ServiceOrder.id.desc())).all()

    def booking_usages(self, booking_id):
        return self.db.scalars(select(ServiceUsage).where(ServiceUsage.booking_id == booking_id)
            .options(joinedload(ServiceUsage.service)).order_by(ServiceUsage.id.desc())).all()

    def promotions(self):
        return self.db.scalars(select(Promotion).order_by(Promotion.id.desc())).all()
