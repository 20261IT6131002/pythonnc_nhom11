"""Smoke tests cho cấu trúc module, không cần màn hình hoặc kết nối MySQL."""
import os

os.environ['GRANDSTAY_TEST_MODE'] = '1'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'


def test_model_modules_share_one_sqlalchemy_registry():
    from hotel.models.database import Base
    from hotel.models import entities
    from hotel.models.bookings import Booking
    from hotel.models.rooms import Room
    from hotel.models.users import User

    assert entities.Booking is Booking
    assert entities.Room is Room
    assert entities.User is User
    assert {'users', 'room_types', 'rooms', 'customers', 'bookings', 'invoices',
            'payments', 'hotel_services', 'service_usages', 'audit_logs'} <= set(Base.metadata.tables)


def test_controller_facade_has_required_methods():
    from hotel.controllers.desktop_controller import DesktopController

    for name in ('login', 'logout', 'save_room', 'save_customer', 'book', 'lookup',
                 'set_booking_status', 'make_invoice', 'pay', 'report', 'calendar',
                 'add_user', 'ask_chatbot'):
        assert callable(getattr(DesktopController, name))
    assert DesktopController.book.__module__ == 'hotel.controllers.bookings_controller'


def test_view_components_wired_from_domain_modules():
    from hotel.views.auth.login_view import LoginView
    from hotel.views.customer.dashboard import GuestView
    from hotel.views.desktop import GrandStayApp
    from hotel.views.guest import GuestView as LegacyGuestView
    from hotel.views.staff import StaffView

    assert LoginView.__module__ == 'hotel.views.auth.login_view'
    assert GuestView is LegacyGuestView
    assert callable(getattr(GrandStayApp, 'show_login'))
    assert StaffView._book.__module__ == 'hotel.views.screens.bookings'
    assert StaffView._payment.__module__ == 'hotel.views.screens.billing'
    assert StaffView._dashboard.__module__ == 'hotel.views.receptionist.dashboard'
    assert GuestView.show_rooms.__module__ == 'hotel.views.customer.rooms'
    assert GuestView.show_lookup.__module__ == 'hotel.views.customer.lookup'
