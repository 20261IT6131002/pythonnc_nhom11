# GrandStay - Ứng dụng quản lý khách sạn bằng Tkinter, MVC, Python, MySQL
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

5. Chạy đúng thứ tự:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.seed
   .\.venv\Scripts\python.exe -m scripts.create_admin
   .\.venv\Scripts\python.exe main.py
   ```

   `seed` không chạy chồng khi có loại phòng; `create_admin` hỏi tên/mật khẩu bạn tự đặt, **không có mật khẩu mặc định**. Chỉ cần tạo admin một lần. Những lần mở sau, chạy `main.py` hoặc `CHAY_WINDOWS.bat`.

6. Ứng dụng mở **trang chủ GrandStay**. Chọn **Đăng nhập / Đăng ký** ở góc trên bên phải, dùng tài khoản Admin vừa tạo để vào màn hình quản trị. Khách vẫn có thể xem và tìm phòng công khai.

## Các chức năng đã lập trình

| Nhóm | Chức năng |
|---|---|
| Đăng nhập & quyền | Admin, Lễ tân, Khách hàng; khách đăng ký qua email + OTP; đăng nhập bằng email đã xác minh hoặc username cũ; khôi phục mật khẩu qua OTP; Admin tạo/khóa nhân viên |
| Cấu hình và nhân viên N1 | Đủ sáu bảng N1 `users`, `roles`, `user_roles`, `employees`, `audit_logs`, `system_settings`; Admin quản lý hồ sơ nhân viên và thông tin khách sạn |
| Bảo vệ mật khẩu | PBKDF2-HMAC-SHA256 với salt riêng và 600.000 vòng; hash 310.000 vòng cũ được nâng cấp khi đăng nhập thành công; đổi mật khẩu sau đăng nhập |
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

## Kiểm thử

Chạy kiểm thử nghiệp vụ với **SQLite trong bộ nhớ chỉ dành cho test**, hoàn toàn không sử dụng hoặc thay đổi MySQL của bạn:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Test kiểm tra nghiệp vụ không yêu cầu màn hình; muốn kiểm tra View Tkinter, hãy chạy `main.py` trực tiếp trên máy Windows có desktop.

## N1 — Tài khoản và mật khẩu

- Ở trang chủ chọn **Đăng nhập / Đăng ký**. Khách điền Gmail **và SĐT bắt buộc**, nhận mã OTP vào Gmail, nhập đủ sáu số và mới được tạo tài khoản. SĐT là thông tin tra cứu, **chưa được xác minh bằng SMS**.
- Admin và Lễ tân cũng đăng nhập tại form này, rồi được chuyển vào Dashboard nhân viên phù hợp với quyền hiện có.
- Admin đầu tiên tạo bằng `scripts.create_admin` cũng phải khai báo email và nhập OTP được gửi qua SMTP; chỉ lưu vào MySQL sau khi xác minh email.
- Admin/Lễ tân cũ vẫn đăng nhập bằng username. Tài khoản nhân viên **tạo mới bắt buộc khai báo email** ngay khi cấp. Các tài khoản cũ chưa có email có thể được Admin khác bổ sung qua **Tài khoản → Nhân viên → nhấp đúp vào dòng → Gán / sửa Gmail**; không còn nút xác minh email trên header.
- Ở mục **Quên mật khẩu**, nhập email đã xác minh, gửi mã và đặt mật khẩu mới. Mã hết hạn sau 10 phút, dùng một lần, tối đa 5 lần nhập sai và giới hạn gửi lại trong 60 giây.
- Nhân viên chọn **Tài khoản của tôi → Đổi mật khẩu**; khách chọn **Tài khoản → Bảo mật tài khoản → Đổi mật khẩu**. Mật khẩu không bao giờ lưu dưới dạng văn bản thuần.
- Admin vào **Tài khoản → Nhân viên**: chỉ có một nút **+ Thêm tài khoản nhân viên** ở phía trên, nhập username, họ tên, SĐT, Gmail, chức vụ, vai trò; hệ thống sinh mật khẩu tạm ngẫu nhiên và **gửi Gmail**, hiệu lực 24 giờ. Nhân viên bắt buộc đổi mật khẩu trước khi dùng nghiệp vụ. Mỗi dòng nhân viên có **Khóa/Mở** và **Xóa vĩnh viễn** bên phải. Xóa bắt nhập chính xác username, loại bỏ `users`, `employees`, `user_roles`; bản ghi đã xóa không còn hiển thị hay đăng nhập. Không xóa tài khoản đang dùng, Admin hoạt động cuối cùng hoặc nhân viên đã lập thanh toán (cần giữ khóa ngoại người lập phiếu). Nhấp đúp dòng để cấp lại mật khẩu tạm, gán Gmail hoặc sửa hồ sơ.
- **Tài khoản → Khách hàng** chỉ là tài khoản khách đã đăng ký online; **Hồ sơ khách lưu trú** gồm cả khách đặt tại quầy không có tài khoản/mật khẩu.
- Đơn đặt tại quầy không bắt buộc Gmail; lễ tân tìm SĐT và đối chiếu danh tính trước khi chọn hồ sơ cũ. Khách đăng ký sau gửi **yêu cầu liên kết lịch sử** bằng mã đặt phòng + SĐT; Admin phải đối chiếu danh tính rồi duyệt. Không tự gộp lịch sử chỉ bằng SĐT.
- Khách đặt online khi chưa đăng nhập xác minh **OTP qua Gmail cho đơn đặt phòng**; khách đã đăng nhập được gắn đơn vào hồ sơ tài khoản của mình.
- Admin chọn **Sửa hồ sơ nhân viên** để cập nhật số điện thoại và chức vụ; chọn **Cấu hình khách sạn** để cập nhật tên, địa chỉ, điện thoại và giờ nhận/trả phòng.
- Khi không còn Admin có thể đăng nhập, quản trị viên máy chủ có quyền truy cập MySQL và `.env` được phép khôi phục bằng lệnh dưới đây. Lệnh yêu cầu xác nhận thủ công, không in mật khẩu ra màn hình:

  ```powershell
  .\.venv\Scripts\python.exe -m scripts.reset_password
  ```

**Bảo mật:** Đây là *hash một chiều*, không phải mã hóa hai chiều có thể giải mã. Mỗi tài khoản dùng salt ngẫu nhiên; hàm so khớp dùng `hmac.compare_digest`. Tài khoản dùng hash PBKDF2 310.000 vòng từ phiên bản cũ vẫn đăng nhập được và được nâng lên 600.000 vòng một cách tự động.

### Cấu hình SMTP gửi OTP trên Windows

Mở `.env` hiện có của dự án, **không ghi đè file này** khi cập nhật bản N1. Thêm các biến:

```dotenv
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_SECURITY=starttls
EMAIL_SMTP_USER=diachi-cua-ban@gmail.com
EMAIL_SMTP_PASSWORD=mat_khau_ung_dung_16_ky_tu
EMAIL_FROM=diachi-cua-ban@gmail.com
EMAIL_OTP_SECRET=mot_chuoi_bi_mat_ngau_nhien_dai
```

Với Gmail, cần bật xác minh hai bước và dùng **App Password**, không nhập mật khẩu Gmail chính. Một số tài khoản tổ chức hoặc cấu hình bảo vệ đặc biệt không cho tạo App Password; có thể dùng SMTP nhà cung cấp khác có SSL/TLS.

Tạo khóa bí mật OTP bằng lệnh:

```powershell
py -c "import secrets; print(secrets.token_hex(32))"
```

Dán kết quả vào `EMAIL_OTP_SECRET`, giữ kín và không đẩy `.env` lên GitHub. Nếu bỏ trống, ứng dụng tạo khóa theo phiên nên OTP đang chờ sẽ không hợp lệ sau khi khởi động lại.

Kiểm tra dịch vụ gửi email trước khi dùng:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_smtp
```

Ứng dụng không có chế độ OTP giả khi thiếu SMTP. Đăng ký/khôi phục qua email cần kết nối Internet và cấu hình SMTP thành công.

### Kiểm tra MySQL đang dùng và xác nhận tài khoản thật sự được lưu

GrandStay truy vấn trực tiếp MySQL bằng SQLAlchemy và commit mỗi thao tác thành công.
Nếu MySQL Workbench không thấy tài khoản, **đối chiếu tên database** (ví dụ
`grandstay_nhom11` khác `smart_hotel`) bằng lệnh chỉ đọc:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_mysql_accounts
.\.venv\Scripts\python.exe -m scripts.verify_mysql_accounts --username letan
```

Sau đó chọn cùng schema trong MySQL Workbench và chạy:

```sql
SELECT DATABASE();
SELECT id, username, role, active, archived_at FROM users ORDER BY id DESC;
SELECT id, user_id, phone, position FROM employees ORDER BY id DESC;
```


