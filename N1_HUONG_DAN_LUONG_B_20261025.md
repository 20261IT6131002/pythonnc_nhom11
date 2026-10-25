# GrandStay N1 — Ghi đè luồng tài khoản nhân viên B và khách đặt phòng

**Bản cài dành cho Duyên (N1), dự án `D:\pythonnc_nhom11`.**

## 1. Sao lưu trước khi nâng cấp

- Sao lưu cơ sở dữ liệu MySQL hiện có bằng MySQL Workbench hoặc công cụ backup bạn đang sử dụng.
- Trong PowerShell, chạy `cd D:\pythonnc_nhom11`, rồi `git status`. Nếu có file trùng bản cập nhật đang sửa dở, sao lưu/commit trước.
- Giải nén file `GrandStay_N1_LuongB_Full_GhiDe_20261025.zip` trực tiếp vào `D:\pythonnc_nhom11` với `-Force`. **Không xóa dự án cũ, không xóa DB, không xóa `.env`.**

```powershell
cd D:\pythonnc_nhom11
git status
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\GrandStay_N1_LuongB_Full_GhiDe_20261025.zip" -DestinationPath "D:\pythonnc_nhom11" -Force
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.check_smtp
.\.venv\Scripts\python.exe main.py
```

## 2. Cấu hình Gmail OTP (giữ nguyên)

Trong `.env` sẵn có, giữ nguyên `MYSQL_*` và `EMAIL_*` đang chạy; kiểm tra `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_SECURITY`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_OTP_SECRET`. Cách B gửi mật khẩu tạm bằng **chính Gmail SMTP này**, không cần dịch vụ SMS trả phí. Gmail miễn phí trong hạn mức sử dụng, không bảo đảm gửi vô hạn. Không đưa mật khẩu ứng dụng hay `.env` lên GitHub.

## 3. Phân biệt 3 đối tượng dữ liệu

1. **Tài khoản đăng nhập (`users`)**: gồm Admin, lễ tân, khách online. Khách online đăng ký Gmail + OTP + SĐT bắt buộc.
2. **Hồ sơ khách lưu trú (`customers`)**: một khách đến quầy vẫn có hồ sơ và đơn đặt phòng nhưng **không cần tài khoản hay Gmail**.
3. **Đơn đặt phòng (`bookings`)**: luôn giữ khóa `customer_id`. Đơn cũ không bị chuyển sang tài khoản chỉ do trùng SĐT.

Menu Admin có **Tài khoản → Nhân viên / Khách hàng** và menu nghiệp vụ riêng **Hồ sơ khách lưu trú**. Có thêm **Duyệt liên kết lịch sử** dành cho Admin.

## 4. Luồng B — Admin cấp tài khoản nhân viên

Admin đầu tiên có thể tạo bằng `python -m scripts.create_admin`, cần cung cấp
email và mã OTP hợp lệ. Bản ghi Admin chỉ được lưu sau khi xác minh email thành công.

1. Admin đăng nhập → **Tài khoản** → **Nhân viên**.
2. Chọn **+ Thêm tài khoản nhân viên** (nút thêm duy nhất ở phía trên). Nhập username, họ tên, SĐT, Gmail nhân viên, chức vụ và vai trò (`receptionist`/`admin`).
3. Hệ thống sinh mật khẩu tạm ngẫu nhiên bằng `secrets`, chỉ lưu **PBKDF2-SHA256 + salt** trong MySQL và gửi tên đăng nhập + mật khẩu tạm tới Gmail được nhập.
4. Mật khẩu tạm hết hạn sau **24 giờ**. Nhân viên đăng nhập lần đầu phải nhập mật khẩu tạm và **bắt buộc đổi mật khẩu**, nếu hủy không được vào nghiệp vụ. Sai mật khẩu 5 lần liên tiếp sẽ tạm chặn đăng nhập **15 phút**.
5. Khi đổi xong, mật khẩu tạm mất hiệu lực; nhân viên dùng mật khẩu riêng từ lần sau. Có thể đăng nhập qua Gmail đã được xác minh.
6. Mỗi dòng nhân viên có nút **Khóa/Mở** và **Xóa vĩnh viễn** bên phải. Muốn xóa, phải nhập chính xác username: ứng dụng xóa tài khoản cùng hồ sơ nhân viên và vai trò trong MySQL; không còn hiển thị và không thể đăng nhập. Các tài khoản đã ngừng sử dụng từ bản cũ vẫn có thể xóa vĩnh viễn. Nếu nhân viên đã ghi nhận thanh toán, hệ thống từ chối xóa vì cần bảo toàn khóa ngoại người lập phiếu; hãy dùng Khóa. Để **sửa hồ sơ, cấp lại mật khẩu tạm hoặc gán/sửa Gmail**, nhấp đúp vào dòng nhân viên. Không thể khóa/xóa chính tài khoản Admin đang đăng nhập. Danh sách **Khách hàng** trong mục Tài khoản chỉ có quyền xem, không có nút sửa/xóa/khóa.

**Nếu Gmail lỗi:** thao tác cấp tài khoản mới được hủy trong phiên giao dịch DB (không tạo tài khoản hoạt động với mật khẩu không được gửi). Nếu một email đã nhận mật khẩu tạm nhưng việc ghi DB gặp lỗi sau đó, Admin cần thực hiện cấp lại.

**Lưu ý bảo mật:** cách B gửi mật khẩu qua email nên có rủi ro khi hộp thư bị lộ. Không chuyển tiếp email, không chụp gửi mật khẩu lên nhóm chat; luôn đổi ngay sau lần đầu. OTP Gmail hiện có là xác minh/khôi phục email, chưa phải MFA tại mỗi lần đăng nhập.

## 5. Khách đặt trực tiếp và liên kết lịch sử

### Khách không có tài khoản đến quầy

Lễ tân vào **Đặt phòng** → nhập họ tên, SĐT, ngày, số khách và phòng. Gmail **có thể để trống**. Nếu tìm thấy hồ sơ trùng SĐT, ứng dụng đề nghị lễ tân chọn hồ sơ cũ **sau khi đối chiếu danh tính**, hoặc tạo hồ sơ mới. Không tự ghép lịch sử chỉ bằng tên/SĐT.

### Khách muốn đăng ký tài khoản sau này

Khách vào **Đăng ký** → nhập họ tên, username, SĐT, Gmail, mật khẩu → OTP Gmail → tạo tài khoản riêng. Sau khi đăng nhập, vào **Tài khoản khách hàng → Liên kết lịch sử đặt phòng tại quầy**, nhập mã đặt phòng cũ và SĐT.

Hệ thống chỉ tạo **yêu cầu chờ duyệt**. Admin vào **Duyệt liên kết lịch sử**, kiểm tra danh tính/hồ sơ thực tế rồi mới duyệt. Sau đó khách thấy các đơn lịch sử được liên kết. Nếu không còn mã đặt phòng, khách đến quầy để nhân viên hỗ trợ đối chiếu; không có cơ chế tự nhận lịch sử chỉ dựa vào SĐT.

### Khách đặt online

- Đã đăng nhập: đơn đặt được gắn vào hồ sơ khách của tài khoản đó; không cần OTP mỗi đơn.
- Chưa đăng nhập: nhập Gmail để nhận **OTP xác minh cho đơn này**, rồi đặt phòng ở trạng thái chờ lễ tân xác nhận. Không cần tạo mật khẩu.

## 6. MySQL nâng cấp an toàn

Khi chạy `main.py`, migration bổ sung vào **`users`**: `phone` (nullable, unique), `must_change_password`, `temporary_password_expires_at`, `archived_at`, `failed_login_attempts`, `login_blocked_until`; bổ sung vào **`customers`**: `user_id` (nullable, có index); tạo bảng **`customer_link_requests`** cho yêu cầu liên kết.

Các cột mới đều tương thích tài khoản/hồ sơ cũ (NULL hoặc giá trị mặc định). Không xoá các dòng đã có; **không** thay khóa của bảng `bookings`. Tài khoản khách cũ chưa có `phone` có thể vào **Tài khoản khách hàng → Cập nhật số điện thoại** để bổ sung trước khi đặt phòng tiếp.

Không tự tạo ràng buộc duy nhất trên `customers.phone`, vì một số liên hệ có thể xuất hiện trong nhiều hồ sơ. Không tự chuyển tất cả đơn lịch sử có trùng SĐT sang một tài khoản online.

## 7. Checklist thử trước khi push GitHub

1. SMTP tự gửi thử thành công (`python -m scripts.check_smtp`).
2. Admin tạo lễ tân mới có Gmail; Gmail nhận username và mật khẩu tạm.
3. Lễ tân đăng nhập bằng mật khẩu tạm → bị buộc đổi. Hủy form → không vào Dashboard; đổi thành công → được vào.
4. Đăng nhập lại bằng mật khẩu tạm cũ phải thất bại; mật khẩu mới thành công.
5. Admin cấp lại mật khẩu tạm → mật khẩu cũ hết hiệu lực. Mật khẩu tạm quá hạn cần cấp lại.
6. Admin khóa rồi thử đăng nhập tài khoản bị khóa. Tạo thêm một nhân viên thử nghiệm, xác nhận xóa vĩnh viễn bằng đúng username, kiểm tra bản ghi mất khỏi cả giao diện và bảng `users`/`employees` trong đúng schema MySQL; không thử trên tài khoản có thanh toán thật.
7. Admin chuyển tab Tài khoản **Nhân viên / Khách hàng**; kiểm tra mục **Hồ sơ khách lưu trú** hiển thị cả khách chưa có tài khoản.
8. Lễ tân đặt phòng tại quầy **không nhập email** được; kiểm tra trường hợp trùng SĐT có bước chọn và xác minh hồ sơ.
9. Khách đăng ký mới bằng Gmail OTP và SĐT; không được tự thấy lịch sử cũ chỉ nhờ trùng SĐT.
10. Khách gửi yêu cầu liên kết bằng mã đặt phòng cũ; Admin xác minh, phê duyệt → lịch sử hiện lên.
11. Đặt online khi chưa đăng nhập: nhận OTP Gmail, xác minh, đơn được tạo ở trạng thái chờ.
12. Kiểm thử tự động (SQLite giả lập, không đụng MySQL):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

**Lưu ý:** Không có công cụ dựng giao diện Windows/MySQL thật trong môi trường kiểm thử tự động; phải chạy thử MySQL migration và các form trên máy của Duyên trước khi push nhánh N1. Không lưu mật khẩu tạm hoặc mã OTP vào tài liệu/chụp màn hình công khai.
