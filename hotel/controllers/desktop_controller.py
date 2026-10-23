"""Single API facade used by Tkinter Views; implementation is split by domain."""
from hotel.controllers.base import BaseController
from hotel.controllers.utils import vnd
from hotel.controllers.auth_controller import AuthControllerMixin
from hotel.controllers.catalog_controller import CatalogControllerMixin
from hotel.controllers.rooms_controller import RoomsControllerMixin
from hotel.controllers.customers_controller import CustomersControllerMixin
from hotel.controllers.services_controller import ServicesControllerMixin
from hotel.controllers.admin_controller import AdminControllerMixin
from hotel.controllers.bookings_controller import BookingsControllerMixin
from hotel.controllers.billing_controller import BillingControllerMixin
from hotel.controllers.chat_controller import ChatControllerMixin


class DesktopController(AuthControllerMixin, CatalogControllerMixin, RoomsControllerMixin, CustomersControllerMixin, ServicesControllerMixin, AdminControllerMixin, BookingsControllerMixin, BillingControllerMixin, ChatControllerMixin, BaseController):
    """UI-facing Controller, composed from focused domain controllers."""
    pass
