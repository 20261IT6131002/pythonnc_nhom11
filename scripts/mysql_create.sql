-- Chạy với tài khoản có quyền tạo database, ví dụ MySQL Workbench.
CREATE DATABASE IF NOT EXISTS grandstay_nhom11
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- THAY chuỗi MAT_KHAU_MANH_O_DAY trước khi chạy. Không dùng user root trong app.
CREATE USER IF NOT EXISTS 'grandstay_app'@'localhost' IDENTIFIED BY 'MAT_KHAU_MANH_O_DAY';
CREATE USER IF NOT EXISTS 'grandstay_app'@'127.0.0.1' IDENTIFIED BY 'MAT_KHAU_MANH_O_DAY';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
  ON grandstay_nhom11.* TO 'grandstay_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
  ON grandstay_nhom11.* TO 'grandstay_app'@'127.0.0.1';

-- Nếu user đã tồn tại, CREATE USER IF NOT EXISTS KHÔNG đổi mật khẩu cũ.
-- Khi cần đổi, dùng ALTER USER 'grandstay_app'@'localhost' IDENTIFIED BY '...';
-- Schema tables được tạo bởi scripts.seed / main.py thông qua SQLAlchemy ORM.
