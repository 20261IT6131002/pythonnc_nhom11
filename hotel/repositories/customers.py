"""Queries for N3 profiles, stays and customer spending."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from hotel.models.entities import Booking, BookingGuest, Customer, Invoice, Payment


class CustomerRepository:
    def __init__(self, db):
        self.db = db

    def search(self, query=''):
        statement = select(Customer)
        query = str(query).strip()
        if query:
            terms = [Customer.full_name.icontains(query, autoescape=True),
                     Customer.phone.contains(query, autoescape=True),
                     Customer.email.icontains(query, autoescape=True)]
            if query.isdigit():
                terms.append(Customer.id == int(query))
            statement = statement.where(or_(*terms))
        return self.db.scalars(statement.order_by(Customer.id.desc()).limit(500)).all()

    def bookings(self, customer_ids):
        return self.db.scalars(select(Booking).where(Booking.customer_id.in_(customer_ids))
            .options(joinedload(Booking.room), joinedload(Booking.invoice))
            .order_by(Booking.id.desc())).all()

    def paid_total(self, customer_ids):
        return self.db.scalar(select(func.sum(Payment.amount)).join(Invoice).join(Booking)
                              .where(Booking.customer_id.in_(customer_ids))) or 0

    def staying(self):
        return self.db.scalars(select(Booking).where(Booking.status == 'checked_in')
            .options(joinedload(Booking.room), joinedload(Booking.customer))
            .order_by(Booking.checked_in_at.desc())).all()

    def guests(self, booking_id):
        return self.db.scalars(select(BookingGuest).where(BookingGuest.booking_id == booking_id)
            .order_by(BookingGuest.is_primary.desc(), BookingGuest.id)).all()
