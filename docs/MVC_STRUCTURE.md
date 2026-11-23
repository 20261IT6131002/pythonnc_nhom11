# GrandStay — Cấu trúc MVC sau khi chia module

Mục tiêu: giữ nguyên giao diện Tkinter, các thao tác nghiệp vụ và database, đồng thời tránh
việc nhiều thành viên cùng sửa một file View/Controller quá lớn.

## 1. View — `hotel/views/`

| Đường dẫn | Phần việc | Không nên chứa |
| --- | --- | --- |
| `desktop.py` | Tạo cửa sổ chính, chuyển giữa Guest, Login, Staff | SQL, nghiệp vụ đặt phòng |
| `pages.py` | Cấu hình trang, tiêu đề, cột bảng | Truy vấn database |
| `auth/login_view.py` | Form đăng nhập nhân viên | Xác minh mật khẩu trực tiếp |
| `customer/dashboard.py` | Bố cục chung và thanh menu khách | Quy tắc đặt phòng |
| `customer/home.py`, `rooms.py`, `lookup.py`, `services.py`, `chat.py` | Các trang khách, popup tư vấn | SQLAlchemy |
| `staff.py` | Khung chung Admin/Lễ tân, điều phối trang | Quy tắc nghiệp vụ |
| `receptionist/dashboard.py` | Thẻ thống kê, bảng đặt phòng gần đây | Truy vấn trực tiếp |
| `admin/dashboard.py` | Bộ lọc và bảng báo cáo doanh thu | Tính toán SQL |
| `screens/rooms.py` | Form phòng/loại phòng | Ghi ORM trực tiếp |
| `screens/bookings.py` | Form đặt, nhận/trả và lịch phòng | Trạng thái ghi DB trực tiếp |
| `screens/customers.py`, `services.py` | Form hồ sơ khách, danh mục dịch vụ | Lệnh SQL |
| `screens/billing.py`, `admin.py`, `chat.py` | Thanh toán/PDF, nhân viên, chat | Xử lý MySQL trực tiếp |
| `components/sidebar.py`, `theme.py`, `widget_helpers.py` | Thanh menu, token giao diện, dialog/tree tái sử dụng | Logic doanh thu, đặt phòng |

Các màn hình nghiệp vụ được viết dưới dạng *Mixin* (`RoomsScreenMixin`,
`BookingsScreenMixin`...). `StaffView` kết hợp những Mixin này để các lệnh gọi
`self._book()`, `self._payment()`... vẫn hoạt động như trước. Tương tự,
`GuestView` kết hợp các Mixin khách hàng. Đây là chia lớp theo thành phần của
Tkinter, **không tạo nhiều `Tk()`**.

## 2. Controller — `hotel/controllers/`

| Module | Chức năng |
| --- | --- |
| `desktop_controller.py` | `DesktopController` là facade duy nhất cho View |
| `base.py` | Quản lý session, xác thực lại quyền, lấy bản ghi |
| `auth_controller.py` | Đăng nhập, đăng xuất |
| `catalog_controller.py` | Danh sách bảng, dữ liệu công khai, tổng quan |
| `rooms_controller.py` | Loại phòng, phòng, phòng khả dụng |
| `bookings_controller.py` | Đặt phòng, tra cứu, đổi trạng thái, lịch phòng |
| `customers_controller.py` | Cập nhật hồ sơ khách |
| `services_controller.py` | Dịch vụ và phát sinh dịch vụ |
| `billing_controller.py` | Hóa đơn, thanh toán, doanh thu, PDF |
| `admin_controller.py` | Tài khoản nhân viên, kích hoạt/khóa |
| `chat_controller.py` | Điều phối chatbot quy tắc |

Luồng ví dụ: `screens/bookings.py` (nút Đặt phòng) →
`DesktopController.book()` (triển khai tại `bookings_controller.py`) →
`services/business.py` (kiểm tra ngày, chồng lịch, tạo đơn) →
`models/bookings.py` / MySQL.

## 3. Model và tầng truy cập dữ liệu

`hotel/models/database.py` quản lý SQLAlchemy Engine/Session. Các bảng được
phân theo nhóm: `users.py`, `rooms.py`, `customers.py`, `bookings.py`,
`services.py`, `billing.py`, `audit.py`. `entities.py` chỉ tập hợp import cho
những phần code cũ; **không được khai báo lại các bảng** trong file này.

`hotel/repositories/catalog.py` giữ các truy vấn đọc ORM tập trung.
`hotel/services/` giữ quy tắc đặt phòng, thanh toán, thay đổi dữ liệu và tạo PDF.
Đây là các tầng hỗ trợ Model; không chứa Widget Tkinter.

## 4. Hướng dẫn làm việc nhóm

1. Khi làm tính năng mới, viết giao diện vào đúng `views/screens/` hoặc `views/customer/`.
2. Thêm phương thức điều phối vào `controllers/*_controller.py` tương ứng.
3. Thêm quy tắc dữ liệu trong `services/`, câu truy vấn đọc trong `repositories/`.
4. Chỉ sửa `models/` khi thực sự thay đổi schema; cân nhắc migration nếu database đã có dữ liệu.
5. Kiểm tra bằng `python -m pytest -q` và chạy `python main.py` trên Windows có Tkinter và MySQL.

Ghi chú: tên package tiếp tục là **`hotel`** thay vì đổi sang **`app`** để không
phá vỡ các import hiện tại. Các tên module trong cây View đề xuất đã được giữ
tương đương bên dưới `hotel/views/`.
