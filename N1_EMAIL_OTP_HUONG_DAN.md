# Cập nhật N1 Email OTP trên ổ D

## 1. Sao lưu trước khi ghi đè

Trong PowerShell:

```powershell
cd D:\pythonnc_nhom11
git status
```

Nếu có sửa đổi chưa commit ở những file thuộc N1, hãy sao lưu hoặc commit chúng trước khi dùng bản cập nhật. ZIP N1 chỉ ghi đè các file có trong gói, không xóa `.env` hay dữ liệu MySQL.

Giải nén file ZIP cập nhật vào `D:\pythonnc_nhom11` với tùy chọn **ghi đè**.

## 2. Cấu hình email gửi OTP

Mở file `.env` **đang sử dụng**:

```powershell
notepad D:\pythonnc_nhom11\.env
```

Giữ nguyên các biến `MYSQL_*`. Thêm:

```dotenv
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_SECURITY=starttls
EMAIL_SMTP_USER=ten-ban@gmail.com
EMAIL_SMTP_PASSWORD=MAT_KHAU_UNG_DUNG
EMAIL_FROM=ten-ban@gmail.com
EMAIL_OTP_SECRET=CHUOI_BI_MAT_64_KY_TU_HEX
```

Với Gmail, bật **Xác minh 2 bước** và tạo **Mật khẩu ứng dụng (App Password)** trên tài khoản Google nếu tài khoản được hỗ trợ. Không sử dụng mật khẩu Gmail chính. Không gửi mật khẩu ứng dụng hoặc `.env` lên GitHub hay trong cuộc trò chuyện.

Tạo khóa OTP bằng lệnh:

```powershell
py -c "import secrets; print(secrets.token_hex(32))"
```

Dán kết quả vào `EMAIL_OTP_SECRET`.

## 3. Kiểm tra gửi email

```powershell
cd D:\pythonnc_nhom11
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.check_smtp
```

Nếu gửi thành công, kiểm tra hộp thư Inbox/Spam. Sau đó chạy:

```powershell
.\.venv\Scripts\python.exe main.py
```

Chương trình tự bổ sung cột `email`, `email_verified_at`, index email và bảng `email_otps` vào MySQL nếu còn thiếu, không xóa tài khoản cũ. Bạn nên sao lưu database trước lần chạy nâng cấp schema.

## 4. Kiểm thử các luồng

1. Khách đăng ký với tên, username, email, mật khẩu; nhận OTP và xác minh.
2. Đăng xuất rồi đăng nhập bằng email/mật khẩu.
3. Thử OTP sai, OTP dùng lại, gửi lại dưới 60 giây.
4. Quên mật khẩu qua email, đặt lại, đăng nhập bằng mật khẩu mới.
5. Admin/Lễ tân cũ đăng nhập bằng username, vào **Xác minh email** để liên kết email.
6. Kiểm tra lại Dashboard và các chức năng N2–N5 có sẵn.

Chạy test tự động (không gửi email thật, không chạm MySQL):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Sau khi kiểm thử ổn, xem `git status` và chỉ commit các file thực sự thuộc phần cập nhật N1.

**Ghi chú bảo mật:** Mật khẩu được hash một chiều với PBKDF2-HMAC-SHA256 và salt; OTP được lưu dưới dạng HMAC, chỉ dùng một lần và hết hạn sau 10 phút. Dữ liệu phòng, khách và email trong MySQL chưa được mã hóa toàn bộ ở mức ứng dụng.
