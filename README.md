# GrandStay - Ứng dụng quản lý khách sạn bằng Tkinter, MVC, Python, MySQL

**Bản desktop đúng yêu cầu Nhóm 11.** Khác ZIP gốc là website FastAPI, bản này chạy trong **cửa sổ Tkinter trên Windows**, không mở localhost hay trình duyệt. Có thể chạy Python 3.11–3.13, MySQL Server 8.x.

## Giao diện dựa trên đúng mẫu gốc

- Giữ nhận diện **GrandStay** và bảng màu web cũ: xanh navy `#19334d`, sidebar `#173149`, vàng `#c9a36d`, nền quản trị `#f6f8fb`, thẻ nội dung trắng.
- Trang chủ mở khi chạy: logo G, thanh menu, banner nghỉ dưỡng, minh họa tòa khách sạn, form tìm phòng, thẻ loại phòng, dịch vụ, tra cứu, tư vấn 24/7.
- Quản trị: sidebar theo nhóm Tổng quan / Nghiệp vụ / Quản trị, topbar trắng, dashboard thẻ số liệu và bảng đặt phòng tương tự bố cục cũ.
- Hình minh họa được **vẽ bằng Canvas trong Tkinter**, không phụ thuộc ảnh mạng; đây là bản tái tạo giao diện native theo mẫu, **không phải bản hiển thị HTML/CSS pixel-perfect** (Tkinter không hỗ trợ toàn bộ CSS web).

## Cấu trúc MVC

```text
GrandStay_Tkinter_MVC_Nhom11/
├── main.py                       # Tạo duy nhất một tk.Tk(), kiểm tra kết nối MySQL
├── hotel/
│   ├── config.py                 # Đọc cấu hình MySQL từ .env
│   ├── views/                    # VIEW: chỉ Tkinter và sự kiện người dùng
│   │   ├── desktop.py            # Cửa sổ gốc và chuyển màn hình
│   │   ├── pages.py              # Danh mục trang, tiêu đề, cấu hình cột
│   │   ├── staff.py              # Khung giao diện nhân viên; điều phối màn hình
│   │   ├── auth/login_view.py    # Form đăng nhập
│   │   ├── admin/dashboard.py    # Báo cáo của Admin
│   │   ├── receptionist/dashboard.py # Thống kê chung nhân viên
│   │   ├── customer/             # Trang chủ, phòng, đặt, tra cứu, dịch vụ, chat
│   │   ├── components/           # sidebar.py, theme.py, widget_helpers.py
│   │   └── screens/              # rooms, bookings, customers, services,
│   │                             # billing, admin, chat
│   ├── controllers/              # CONTROLLER: chức năng theo nghiệp vụ
│   │   ├── desktop_controller.py # API thống nhất cho View (kết hợp các lớp nhỏ)
│   │   ├── base.py               # Session, phân quyền, kiểm tra đối tượng
│   │   ├── auth_controller.py, admin_controller.py
│   │   ├── rooms_controller.py, bookings_controller.py
│   │   ├── customers_controller.py, services_controller.py
│   │   └── billing_controller.py, catalog_controller.py, chat_controller.py
│   ├── services/                 # SERVICE: đặt phòng, thanh toán, kiểm tra quy tắc, PDF
│   │   ├── business.py
│   │   ├── catalog.py
│   │   ├── security.py
│   │   ├── chatbot.py
│   │   └── pdf_service.py
│   ├── repositories/             # Repository: các truy vấn ORM phục vụ nghiệp vụ
│   │   └── catalog.py
│   └── models/                   # MODEL: bảng ORM, kết nối MySQL
│       ├── database.py
│       ├── users.py, rooms.py, customers.py, bookings.py
│       ├── services.py, billing.py, audit.py, common.py
│       └── entities.py           # Import tương thích từ các module đã tách
├── scripts/
│   ├── mysql_create.sql         # Tạo database MySQL
│   ├── seed.py                  # Loại phòng + phòng + dịch vụ mẫu
│   └── create_admin.py          # Đặt tài khoản Admin đầu tiên
├── tests/                       # Kiểm thử nghiệp vụ, cấu hình và phân lớp MVC
├── .env.example                 # Mẫu cấu hình, KHÔNG có mật khẩu thật
├── requirements.txt
└── CHAY_WINDOWS.bat
```

Luồng xử lý: **Tkinter View → Controller → Service/Repository → SQLAlchemy Model → MySQL**. View không viết SQL, không thao tác trực tiếp với ORM. Controller và Service không hiển thị giao diện. Chỉ có **một `tk.Tk()`** và các màn hình `ttk.Frame` / hộp thoại `tk.Toplevel`.

Các lớp View dùng *Mixin* để chia nhỏ phương thức mà vẫn giữ nguyên bố cục gốc. `GuestView` điều phối các trang khách hàng; `StaffView` điều phối Admin/Lễ tân. `DesktopController` là giao diện nghiệp vụ duy nhất mà View gọi, còn các phương thức được đặt ở từng `*_controller.py`. `entities.py`, `guest.py`, `theme.py` và `widgets.py` là các đường import tương thích với code cũ; code mới nên import trực tiếp từ module đã tách. Tham khảo `MVC_STRUCTURE.md` để nhóm phân công theo file.

## Chạy từng bước trên Windows

1. Cài **Python 3.11 trở lên** (có Tkinter) và **MySQL Community Server 8.x**, bật dịch vụ MySQL. Nên dùng MySQL Workbench.
2. Giải nén ZIP. Trong Workbench, mở `scripts/mysql_create.sql`, **thay mật khẩu ví dụ bằng mật khẩu mạnh của bạn**, chạy script bằng tài khoản đủ quyền. Nếu đã có database `grandstay_nhom11`, script không xóa bảng hay dữ liệu cũ.
3. Mở PowerShell trong thư mục giải nén:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   Copy-Item .env.example .env
   notepad .env
   ```

4. Trong `.env`, sửa các thông số MySQL theo tài khoản/bản MySQL ở bước 2. Ví dụ tài khoản `root` không có mật khẩu:

   ```dotenv
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=
   MYSQL_DATABASE=grandstay_nhom11
   HOTEL_NAME=GrandStay
   ```

   Nếu tài khoản MySQL có mật khẩu, điền trực tiếp vào `MYSQL_PASSWORD`. Chương trình tự mã hóa các ký tự đặc biệt như `@`, `#`, `/`, `:`, `%`, không còn phải chỉnh `DATABASE_URL`. Nên dùng tài khoản `grandstay_app` được tạo trong `scripts/mysql_create.sql` thay vì `root` cho ứng dụng thực tế. **Không tải `.env` lên GitHub**.

   Phần mềm vẫn hỗ trợ cấu hình `DATABASE_URL` cũ nếu bạn không khai báo biến `MYSQL_*`. Nếu có cả hai, `MYSQL_*` được ưu tiên. Các biến `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `EMAIL_*` hoặc `GEMINI_*` từ ZIP web cũ hiện **không** tự kích hoạt các tính năng tương ứng trong bản Tkinter.

5. Chạy đúng thứ tự:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.seed
   .\.venv\Scripts\python.exe -m scripts.create_admin
   .\.venv\Scripts\python.exe main.py
   ```

   `seed` không chạy chồng khi có loại phòng; `create_admin` hỏi tên/mật khẩu bạn tự đặt, **không có mật khẩu mặc định**. Chỉ cần tạo admin một lần. Những lần mở sau, chạy `main.py` hoặc `CHAY_WINDOWS.bat`.

6. Ứng dụng mở **trang chủ GrandStay** theo mẫu gốc. Chọn **Nhân viên đăng nhập** ở góc trên bên phải, dùng tài khoản Admin vừa tạo để vào màn hình quản trị. Khách có thể tìm/đặt phòng ngay ở trang chủ mà không cần tài khoản.

## Các chức năng đã lập trình

| Nhóm | Chức năng |
|---|---|
| Đăng nhập & quyền | Admin, Lễ tân; tạo/khóa tài khoản (Admin), nhật ký hành động |
| Tổng quan | Số phòng, khách, đơn đặt, khách đang lưu trú, tiền thu trong ngày |
| Phòng và loại phòng | Thêm/sửa loại phòng, giá, sức chứa; thêm/sửa/tạm ngừng phòng |
| Khách hàng | Thêm/sửa thông tin, xem lịch sử đặt phòng theo SĐT |
| Đặt phòng | Tìm phòng trống theo ngày & số khách, kiểm tra trùng khoảng ngày, mã BK, đơn khách chờ xác nhận |
| Lễ tân | Xác nhận → nhận phòng → lập hóa đơn/thanh toán → trả phòng, hoặc hủy hợp lệ |
| Lịch phòng | Xem 7/14/30 ngày, từng phòng, các ngày đã đặt/đang ở |
| Dịch vụ | Quản lý giá và trạng thái dịch vụ, thêm phát sinh khi khách đã check-in |
| Hóa đơn | Chốt tiền phòng/dịch vụ, ghi nhận tiền mặt/chuyển khoản/thẻ thủ công, chống thu vượt, xuất PDF |
| Báo cáo | Số tiền thực thu theo khoảng ngày, xuất PDF (Admin) |
| Tư vấn | Chatbot **quy tắc** đọc giá, dịch vụ, phòng còn trống từ MySQL |
| Khách hàng | Tự tìm, gửi yêu cầu đặt phòng, tra cứu bằng mã BK + SĐT |

**Quy định nghiệp vụ:** ngày nhận trước ngày trả; không đặt ngày quá khứ; cấm trùng lịch phòng ở các trạng thái hiệu lực; giá phòng được chốt khi đặt; chỉ thêm dịch vụ trong thời gian đã nhận phòng và trước lúc chốt hóa đơn; không trả phòng nếu hóa đơn còn thiếu tiền.

### Giới hạn cần nói trung thực khi báo cáo

- Đây là sản phẩm desktop học tập; **chưa có email gửi tự động**, hoàn tiền, đặt cọc, đổi lịch đặt, booking nhiều phòng trong một đơn hoặc xử lý giao dịch ngân hàng thật.
- Chatbot dùng quy tắc, **không phải API AI/LLM**.
- Xuất PDF phục vụ nội bộ, không phải hóa đơn điện tử thuế.
- Không có phân hệ bảo trì, dọn phòng, sự cố theo phạm vi Nhóm 11 đã chốt.
- Phần quản lý khách hàng chỉ dành cho Admin/Lễ tân; khách dùng màn hình tự phục vụ, không tạo tài khoản để đăng nhập.
- Không tích hợp migration production; `create_all` chỉ tạo bảng còn thiếu, không tự cập nhật cấu trúc bảng đã có.

## Kiểm thử

Chạy kiểm thử nghiệp vụ với **SQLite trong bộ nhớ chỉ dành cho test**, hoàn toàn không sử dụng hoặc thay đổi MySQL của bạn:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Test kiểm tra nghiệp vụ không yêu cầu màn hình; muốn kiểm tra View Tkinter, hãy chạy `main.py` trực tiếp trên máy Windows có desktop.

## Lỗi thường gặp

- `No module named sqlalchemy/pymysql/dotenv`: cài `requirements.txt` đúng Python trong `.venv`.
- `Access denied for user`: sai user/mật khẩu hoặc `GRANT` MySQL; kiểm tra `MYSQL_USER` và `MYSQL_PASSWORD` trong `.env`.
- `getaddrinfo failed` / máy chủ `@127.0.0.1`: lỗi cấu hình URL cũ. Hãy xóa `DATABASE_URL` trong `.env` và khai báo riêng `MYSQL_HOST=127.0.0.1`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.
- `Can't connect to MySQL server`: kiểm tra MySQL Service (port 3306).
- `Unknown database`: chưa chạy `scripts/mysql_create.sql`.
- Tkinter không khởi chạy: trên Linux cần gói Tk và một desktop/display; bản ưu tiên Windows.
- Đừng giải nén `.venv` từ ZIP web cũ; môi trường ảo Windows cũ không tái dùng được trên máy khác.
