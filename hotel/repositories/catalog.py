from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload
from hotel.models.entities import AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User


class HotelRepository:
    def __init__(self, db: Session):
        self.db = db

    def one(self, model, row_id):
        return self.db.get(model, int(row_id))

    def types(self):
        return self.db.scalars(select(RoomType).order_by(RoomType.id)).all()

    def rooms(self):
        return self.db.scalars(select(Room).options(joinedload(Room.room_type)).order_by(Room.number)).all()

    def customers(self):
        return self.db.scalars(select(Customer).order_by(Customer.id.desc()).limit(500)).all()

    def bookings(self):
        return self.db.scalars(select(Booking).options(joinedload(Booking.customer), joinedload(Booking.room))
                               .order_by(Booking.id.desc()).limit(500)).all()

    def services(self):
        return self.db.scalars(select(HotelService).order_by(HotelService.id)).all()

    def invoices(self):
        return self.db.scalars(select(Invoice).options(
            joinedload(Invoice.booking).joinedload(Booking.customer), selectinload(Invoice.payments))
            .order_by(Invoice.id.desc()).limit(500)).all()

    def users(self):
        return self.db.scalars(select(User).order_by(User.id)).all()

    def logs(self):
        return self.db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(200)).all()

    def count(self, model):
        return self.db.scalar(select(func.count()).select_from(model)) or 0

    def count_bookings_with_status(self, status):
        return self.db.scalar(select(func.count()).select_from(Booking)
                              .where(Booking.status == status)) or 0
