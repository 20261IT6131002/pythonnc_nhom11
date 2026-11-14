# Phân hệ khách hàng và dịch vụ N3

Triển khai theo phạm vi N3 trong tài liệu phân tích tổng thể. Dữ liệu lưu trú
tiếp tục lấy từ `Booking.status`, `checked_in_at` và `checked_out_at` của N2.
Danh sách người đi cùng được quản lý theo từng đặt phòng hiện có.

## Chức năng và cách dùng

- **Hồ sơ khách hàng** tìm theo tên, SĐT, email hoặc ID khách. Thêm, sửa họ tên,
  giấy tờ, ngày sinh, địa chỉ, sở thích, yêu cầu đặc biệt và đoàn hoặc doanh nghiệp.
  Nhân viên phân loại Khách mới, Khách quen, VIP, Doanh nghiệp hoặc Khách đoàn.
  Nút **Lịch sử khách** hiển thị đặt phòng, lưu trú và tổng tiền thực đã thu.
- **Khách đang lưu trú** lấy các đơn đã nhận phòng. Nút **Danh sách người lưu trú**
  khai báo cả người đại diện và người đi cùng, trong số khách và sức chứa của đơn.
  Có thể mở cùng danh sách từ trang Đặt / nhận / trả phòng.
- **Dịch vụ** cho Admin quản lý tên, nhóm, đơn vị, giá, trạng thái cung cấp,
  thời lượng, số suất và yêu cầu lịch hẹn.
- **Yêu cầu dịch vụ** cho khách đăng nhập hoặc nhân viên tạo yêu cầu trên đơn đã
  nhận phòng và chưa chốt hóa đơn. Nhân viên xác nhận rồi hoàn thành hoặc hủy.
  Khách chỉ hủy yêu cầu của mình khi còn chờ xác nhận.
- **Khuyến mãi** cho Admin quản lý mã giảm phần trăm hoặc số tiền, mức tiền phòng
  tối thiểu, thời gian hiệu lực và giới hạn sử dụng. Nhân viên hoặc khách sở hữu
  đơn có thể áp dụng trước khi chốt hóa đơn. Form đặt phòng có ô nhập mã.
- **Tài khoản khách hàng** có thêm cập nhật hồ sơ, tổng chi tiêu, đăng ký dịch vụ
  và áp dụng mã. SĐT và email bảo mật tiếp tục đi qua quy trình tài khoản N1.

## Cấu trúc MVC và điểm tích hợp

| Tầng | Module | Vai trò |
| --- | --- | --- |
| Model | `hotel/models/customer_services.py` | Bảy bảng mở rộng, cùng `Base` hiện có |
| Repository | `hotel/repositories/customers.py`, `services.py` | Truy vấn hồ sơ, lưu trú, chi tiêu và yêu cầu |
| Service | `hotel/services/customers.py`, `service_orders.py`, `promotions.py` | Kiểm tra dữ liệu, sở hữu đơn, lịch hẹn và giao dịch |
| Controller | `customers_controller.py`, `services_controller.py`, `promotions_controller.py` | Xác thực phiên và trả dữ liệu cho View qua `DesktopController` |
| View | `views/screens/customers.py`, `services.py`, `promotions.py`, `views/customer/profile.py`, `services.py` | Form Tkinter và sự kiện |

Các phương thức tích hợp của `DesktopController` gồm `search_customers`,
`customer_details`, `own_customer_profile`, `save_own_customer_profile`,
`staying_customers`, `booking_guests`, `save_booking_guest`, `service_catalog`,
`service_bookings`, `request_service`, `service_orders`, `set_service_order_status`,
`promotions`, `save_promotion` và `apply_promotion`.

Các API sẵn có như `save_customer`, `save_service`, `add_usage`, `book`,
`make_invoice`, `pay` và đường import `models.entities` tiếp tục sử dụng được.
`book` nhận thêm khóa tùy chọn `promotion_code`. `save_customer` và `save_service`
nhận thêm các trường mở rộng nhưng vẫn chấp nhận bộ dữ liệu cũ.

N4 đọc phí dịch vụ hoàn thành từ `service_usages` như trước. Mỗi yêu cầu có một
`usage_id` duy nhất. Hóa đơn lấy giảm giá từ `booking_promotions`, lưu vào cột
`discount_amount` hiện có và xuất dòng giảm giá trên PDF.

## Quy tắc giao dịch

- Một yêu cầu dịch vụ có chuỗi `pending → confirmed → completed` hoặc
  `pending/confirmed → cancelled`. Hoàn thành lại cùng yêu cầu trả về cùng khoản phí.
- Đơn giá và thời lượng được chụp khi đăng ký. Thay đổi danh mục sau đó giữ nguyên
  các yêu cầu đã tạo. `request_token` giúp người gọi gửi lại cùng yêu cầu mà không
  tạo thêm đơn. Một token phải đi cùng nội dung và người gửi ban đầu.
- Lịch hẹn dùng giờ Việt Nam UTC+7, phải ở tương lai và trong kỳ lưu trú. Ngày
  trả phòng nhận lịch đến giờ checkout cấu hình trong `system_settings`.
  Các yêu cầu chờ và đã xác nhận cùng giữ suất. Lịch liên tiếp được phép.
- Cần hoàn thành hoặc hủy mọi yêu cầu còn mở trước khi chốt hóa đơn.
  Nút ghi nhận dịch vụ cũ vẫn ghi phí trực tiếp cho dịch vụ thông thường.
  Dịch vụ có lịch hẹn đi qua luồng yêu cầu để kiểm tra số suất.
- Mỗi đặt phòng áp dụng tối đa một mã, giảm trên tiền phòng và tối đa bằng tiền
  phòng. Ngày hiệu lực xét tại thời điểm áp dụng. Lượt được sử dụng khi áp dụng
  thành công và được giữ cả khi hủy đơn. Mức giảm đã chốt được giữ khi Admin sửa
  chương trình. Gửi lại cùng mã trên cùng đơn giữ nguyên mức giảm và số lượt.
- Các thao tác ghi N3 khóa dòng đặt phòng và dòng danh mục liên quan. Controller
  mở giao dịch MySQL `READ COMMITTED` để tránh gap lock ở token và bản chụp chưa
  tồn tại. Khi gọi Service trực tiếp từ module mới, mở giao dịch theo cùng cách.
- Hồ sơ đã liên kết tài khoản giữ quy tắc SĐT và duyệt liên kết của N1. Khách tự
  cập nhật thông tin cá nhân trên hồ sơ của mình, còn phân loại do nhân viên quản lý.

## Tương thích dữ liệu và khởi động

Bảy bảng bổ sung gồm `customer_profiles`, `booking_guests`, `service_details`,
`service_orders`, `promotions`, `booking_promotions`, `invoice_customer_snapshots`.
Mở ứng dụng bằng lệnh dưới đây sẽ tạo các bảng còn thiếu qua `Base.metadata.create_all`.

```powershell
.\.venv\Scripts\python.exe main.py
```

Khách và dịch vụ cũ dùng giá trị mặc định khi chưa có bản ghi mở rộng.
Hóa đơn mới lưu bản chụp thông tin khách. Với hóa đơn cũ, lần sửa hồ sơ đầu tiên
sau khi cài N3 sẽ chụp thông tin hiện có trước khi sửa. Thông tin đã bị sửa từ
trước khi cài N3 cần được đối chiếu với chứng từ gốc nếu cần khôi phục.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Bộ kiểm thử mặc định chạy với SQLite tách biệt. Kiểm thử MySQL tại
`tests/test_n3_mysql.py` được bật bằng biến môi trường
`GRANDSTAY_N3_MYSQL_TEST_URL`, với tài khoản MySQL có quyền tạo database thử.
Test tạo database tên ngẫu nhiên `grandstay_n3_check_*`, kiểm tra lịch hẹn đồng
thời, hoàn thành một lần, giới hạn mã và chốt hóa đơn đồng thời, rồi dọn đúng
database thử đó. Giữ thông tin đăng nhập thử trong biến môi trường tại máy chạy.
