"""Stable imports for services and existing integrations."""
from hotel.models.common import utc_now
from hotel.models.users import User
from hotel.models.rooms import RoomType, Room
from hotel.models.customers import Customer
from hotel.models.bookings import Booking
from hotel.models.services import HotelService, ServiceUsage
from hotel.models.billing import Invoice, Payment
from hotel.models.audit import AuditLog
from hotel.models.n1_core import Role, UserRole, Employee, SystemSetting, EmailOtp, CustomerLinkRequest
from hotel.models.customer_services import (BookingGuest, BookingPromotion, CustomerProfile,
                                           InvoiceCustomerSnapshot, Promotion, ServiceDetails, ServiceOrder)
