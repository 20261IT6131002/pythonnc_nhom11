# GrandStay N1 — Giao diện 50/50, tài khoản nhân viên và bảo mật MySQL

## Cập nhật giao diện

- Trang đăng nhập/đăng ký dùng hai cột đều nhau: minh họa khách sạn ở trái, form ở phải.
- Trong form có hai nút lớn **ĐĂNG NHẬP** và **ĐĂNG KÝ**. Trang **Quên mật khẩu** truy cập từ liên kết dưới nút đăng nhập.
- Form dài (đăng ký, quên mật khẩu) có thanh cuộn ở bên phải và hỗ trợ lăn chuột; nút gửi OTP và xác nhận không bị mất khi cửa sổ nhỏ.
- Không đổi giao diện các màn hình do N2–N5 phụ trách.

## Luồng khách hàng và nhân viên

| Trường hợp | Hành động | Điều kiện bảo mật |
| --- | --- | --- |
| Khách đăng ký | ĐĂNG KÝ → nhập tên, username, email, mật khẩu → gửi OTP → nhập OTP → tạo tài khoản | Chỉ tạo vai trò `customer`; OTP email hiệu lực 10 phút, 1 lần dùng, tối đa 5 lần nhập sai, chờ 60 giây mới gửi lại |
| Khách đăng nhập | ĐĂNG NHẬP → email đã xác minh hoặc username + mật khẩu | Chuyển vào giao diện khách |
| Nhân viên mới | Admin đăng nhập → **Nhân viên & quyền** → **Thêm nhân viên** → chọn `receptionist` hoặc `admin` | Người dùng tự đăng ký KHÔNG được tự nâng quyền lên nhân viên/Admin |
| Nhân viên đăng nhập lần đầu | ĐĂNG NHẬP → username do Admin cấp + mật khẩu do Admin bàn giao | Đưa vào giao diện nhân viên theo vai trò |
| Nhân viên liên kết email | Khi đã đăng nhập → **Xác minh email** → nhập mật khẩu hiện tại + email → nhập OTP | Email được lưu và đánh dấu xác minh sau khi nhập OTP đúng |
| Nhân viên quên mật khẩu **đã liên kết email** | Quên mật khẩu → nhập email đã xác minh → nhận OTP → đặt mật khẩu mới | Mật khẩu cũ hết hiệu lực, phiên đăng nhập cũ hết quyền khi kiểm tra tiếp |
| Nhân viên quên mật khẩu **chưa liên kết email** | Liên hệ Admin → **Nhân viên & quyền** → **Đặt lại mật khẩu** | Không thể gửi OTP khi `users.email` đang là `NULL`; mật khẩu cấp mới phải được chuyển riêng cho nhân viên |
| Admin duy nhất quên mật khẩu và chưa có email | Quản trị viên máy chủ có quyền truy cập DB, `.env` chạy `python -m scripts.reset_password` | Chỉ dùng chức năng khôi phục cục bộ sau khi xác minh chủ sở hữu hợp lệ |

**Quan trọng:** tài khoản nhân viên `admin`, `letan` hoặc `duyenad` trong database trước đây có `email = NULL` vẫn đăng nhập được bằng **username**. Để quên mật khẩu qua email hoạt động, từng người phải liên kết và xác minh email trước khi quên mật khẩu.

## Phân biệt hash và mã hóa MySQL

- Cột `users.password_hash` là **PBKDF2-HMAC-SHA256** và `salt` riêng cho từng tài khoản, không phải mã hóa hai chiều; hiện dùng 600.000 vòng. Hash cũ 310.000 vòng được nâng cấp khi đăng nhập đúng.
- Bảng `email_otps.code_digest` lưu **HMAC-SHA256** của mã OTP, kết hợp khóa `EMAIL_OTP_SECRET`, `salt` và mục đích sử dụng; không lưu mã OTP gốc.
- Các cột `users.username`, `users.full_name`, `users.email` và dữ liệu nghiệp vụ N2–N5 **vẫn là dữ liệu thường trong MySQL**. Hash mật khẩu KHÔNG đồng nghĩa cả database đã được mã hóa.
- Gửi OTP qua SMTP dùng STARTTLS (587) hoặc TLS trực tiếp (465), nếu cấu hình và kiểm tra gửi thành công.

### Kiểm tra hiện trạng trong MySQL Workbench (chỉ đọc)

Chọn đúng schema đang được cấu hình trong `.env` (`MYSQL_DATABASE`), rồi chạy:

```sql
SELECT VERSION() AS mysql_version;
SHOW VARIABLES LIKE 'require_secure_transport';
SHOW VARIABLES LIKE 'default_table_encryption';

SELECT username, role, email, email_verified_at,
       LEFT(password_hash, 21) AS hash_prefix
FROM users
ORDER BY id;

SELECT NAME, SPACE_TYPE, ENCRYPTION
FROM INFORMATION_SCHEMA.INNODB_TABLESPACES
WHERE NAME LIKE 'grandstay_nhom11/%';
```

**Sửa `grandstay_nhom11` ở điều kiện cuối thành tên `MYSQL_DATABASE` thật của bạn.** Trường `ENCRYPTION='Y'` thể hiện tablespace tương ứng được mã hóa ở trạng thái lưu trữ, `N` thể hiện chưa. Truy vấn `INNODB_TABLESPACES` có thể cần quyền `PROCESS`. `default_table_encryption` là thiết lập mặc định, không tự chứng minh mọi bảng hiện có đã được mã hóa.

Kiểm tra TLS của **chính phiên kết nối** trong Workbench:

```sql
SHOW SESSION STATUS LIKE 'Ssl_cipher';
```

Nếu kết quả có tên thuật toán khác rỗng thì **phiên Workbench này** dùng TLS. **Điều đó chưa chứng minh kết nối từ ứng dụng Python đã dùng TLS**, vì hai chương trình là hai kết nối khác nhau.

### Muốn bảo vệ sâu hơn cần làm gì?

1. **Cấp tài khoản MySQL riêng cho ứng dụng**, chỉ có các quyền cần thiết trên database khách sạn; tránh triển khai bằng `root`. Bảo vệ file `.env`, tuyệt đối không commit `.env` lên GitHub.
2. **Mã hóa khi truyền**: nếu truy cập MySQL qua mạng, cấu hình TLS trên máy chủ MySQL, CA đáng tin cậy và cấu hình PyMySQL/SQLAlchemy để xác thực chứng chỉ máy chủ. Có thể yêu cầu `require_secure_transport=ON` sau khi đã thử nghiệm mọi client; bật trước khi client hỗ trợ TLS có thể làm ứng dụng mất kết nối.
3. **Mã hóa khi lưu (encryption at rest)**: MySQL InnoDB hỗ trợ mã hóa tablespace, nhưng phải cấu hình **keyring** thích hợp cho phiên bản/edition MySQL và phương án lưu, sao lưu khóa trước. Sao lưu database trước khi chuyển đổi. Không tự chạy `ALTER TABLE ... ENCRYPTION='Y'` nếu chưa thiết lập keyring hoặc chưa có phương án phục hồi.
4. **Mã hóa trường nhạy cảm ở tầng ứng dụng** (CCCD, số điện thoại hoặc dữ liệu khác nếu thực sự cần): cần thiết kế riêng cơ chế AES-GCM, quản lý khóa tách khỏi database, quyền giải mã, tìm kiếm/index và kế hoạch di chuyển dữ liệu. Đây là thay đổi liên quan tới các phân hệ N2–N5, **chưa nằm trong ZIP N1 này**.
5. Giữ máy Windows/MySQL cập nhật, giới hạn quyền truy cập database từ mạng, sao lưu dữ liệu và bảo vệ các bản backup.

Tài liệu đối chiếu:

- OWASP Password Storage: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- OWASP Forgot Password: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html
- MySQL InnoDB data-at-rest: https://dev.mysql.com/doc/refman/8.4/en/innodb-data-encryption.html
- MySQL TLS: https://dev.mysql.com/doc/refman/8.4/en/using-encrypted-connections.html

## Cài cập nhật vào dự án ổ D

Đây là **ZIP nhỏ ghi đè đúng giao diện N1 và thêm tài liệu**, dùng sau khi đã áp dụng bản `GrandStay_N1_EmailOTP_GhiDe_20261025.zip`. Giữ nguyên `.env` và cơ sở dữ liệu của nhóm.

```powershell
cd D:\pythonnc_nhom11
git status
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\GrandStay_N1_UI50_BaoMat_20261025.zip" -DestinationPath "D:\pythonnc_nhom11" -Force
.\.venv\Scripts\python.exe main.py
```

Nếu bạn đang có sửa đổi chưa commit trong `hotel/views/auth/login_view.py`, hãy sao lưu hoặc commit chúng **trước khi giải nén**.

