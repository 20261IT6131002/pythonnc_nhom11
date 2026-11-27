"""Personal profile and promotion actions for the authenticated customer."""
from hotel.views.components.theme import NAVY, WHITE, solid_button, text
from hotel.views.components.widget_helpers import choice_id, error, form_dialog, success
from hotel.views.components.service_details import show_booking_services


class CustomerProfileMixin:
    def _profile_summary(self, section):
        profile = self.c.own_customer_profile()
        text(section, 'HỒ SƠ VÀ CHI TIÊU', 13, NAVY, WHITE, 'bold').pack(anchor='w', pady=(10, 8))
        text(section, f"{profile['booking_count']} đơn đặt · {profile['stay_count']} lượt lưu trú · "
             f"Đã thanh toán {profile['paid_total']}", 11, NAVY, WHITE).pack(anchor='w', pady=(0, 12))
        solid_button(section, 'Cập nhật hồ sơ cá nhân', self.edit_customer_profile, light=True).pack(
            anchor='w', pady=(0, 12))
        solid_button(section, 'Áp dụng mã khuyến mãi', self.apply_customer_promotion, light=True).pack(
            anchor='w', pady=(0, 12))
        solid_button(section, 'Đăng ký / xem yêu cầu dịch vụ', self.show_services, light=True).pack(
            anchor='w', pady=(0, 12))
        solid_button(section, 'Xem dịch vụ & chi phí theo đơn', self.customer_booking_costs, light=True).pack(
            anchor='w', pady=(0, 12))

    def customer_booking_costs(self):
        try:
            bookings = self.c.customer_history()
            if not bookings:
                raise ValueError('Chưa có đặt phòng liên kết với tài khoản.')
            choices = [f"{row['id']} - {row['code']} / Phòng {row['room']}" for row in bookings]
            values = form_dialog(self, 'Chọn đơn xem dịch vụ và chi phí', [
                ('booking', 'Đơn đặt phòng', choices[0], choices),
            ])
            if values is not None:
                show_booking_services(self, self.c, choice_id(values['booking']))
        except Exception as exc:
            error(self, exc)

    def edit_customer_profile(self):
        try:
            profile = self.c.own_customer_profile()
            values = form_dialog(self, 'Hồ sơ cá nhân', [
                ('name', 'Họ tên', profile['name']),
                ('birth_date', 'Ngày sinh (YYYY-MM-DD)', profile['birth_date']),
                ('address', 'Địa chỉ', profile['address']),
                ('organization', 'Đoàn / doanh nghiệp', profile['organization']),
                ('preferences', 'Sở thích', profile['preferences']),
                ('special_requests', 'Yêu cầu đặc biệt', profile['special_requests']),
            ])
            if values is not None:
                self.c.save_own_customer_profile(values)
                success(self, 'Đã lưu hồ sơ cá nhân.')
                self.show_account()
        except Exception as exc:
            error(self, exc)

    def apply_customer_promotion(self):
        try:
            bookings = [row for row in self.c.customer_history()
                        if row['status'] in ('pending', 'confirmed', 'checked_in')]
            if not bookings:
                raise ValueError('Chưa có đơn đặt phòng hiệu lực để áp dụng khuyến mãi.')
            choices = [f"{row['id']} - {row['code']} / Phòng {row['room']}" for row in bookings]
            values = form_dialog(self, 'Mã giảm tiền phòng', [
                ('booking', 'Đơn đặt phòng', choices[0], choices),
                ('code', 'Mã khuyến mãi', ''),
            ])
            if values is not None:
                discount = self.c.apply_promotion(choice_id(values['booking']), values['code'])
                success(self, f'Đã áp dụng giảm {discount} cho tiền phòng của đơn.')
        except Exception as exc:
            error(self, exc)
