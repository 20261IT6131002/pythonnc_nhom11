"""Service request form shared by customer and staff views."""
from uuid import uuid4

from hotel.views.components.widget_helpers import choice_id, form_dialog


def request_service_dialog(parent, controller, service_id=None, booking_id=None):
    bookings = controller.service_bookings()
    if booking_id is not None:
        bookings = [row for row in bookings if row['id'] == booking_id]
    if not bookings:
        raise ValueError('Cần có đơn đã nhận phòng và chưa chốt hóa đơn để đăng ký dịch vụ.')
    services = controller.service_catalog(public=True)
    if service_id is not None:
        services = [row for row in services if row['id'] == service_id]
    if not services:
        raise ValueError('Chưa có dịch vụ đang cung cấp.')
    booking_choices = [f"{row['id']} - {row['code']} / Phòng {row['room']}" for row in bookings]
    service_choices = [f"{row['id']} - {row['name']} ({row['price']}đ/{row['unit']})" for row in services]
    values = form_dialog(parent, 'Đăng ký dịch vụ trong kỳ lưu trú', [
        ('booking', 'Đơn đặt phòng', booking_choices[0], booking_choices),
        ('service', 'Dịch vụ', service_choices[0], service_choices),
        ('quantity', 'Số lượng / số suất', '1'),
        ('scheduled_at', 'Lịch hẹn giờ VN (YYYY-MM-DD HH:MM) nếu cần', ''),
        ('notes', 'Yêu cầu thêm', ''),
    ])
    if values is None:
        return None
    return controller.request_service(choice_id(values['booking']), choice_id(values['service']),
        values['quantity'], scheduled_at=values['scheduled_at'], notes=values['notes'],
        request_token=uuid4().hex)
