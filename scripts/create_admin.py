"""Tạo Admin đầu tiên bằng CLI. Không đặt tài khoản/mật khẩu mặc định trong mã nguồn."""
from __future__ import annotations
import getpass
from sqlalchemy import select
from hotel.models.database import Base,engine,SessionLocal
from hotel.models.entities import User
from hotel.services.security import hash_password
from hotel.services.n1_core import attach_role_and_employee, bootstrap_n1
from hotel.services.email_schema import migrate_email_columns
from hotel.services.email_otp import consume_otp, issue_otp, normalize_email
from hotel.models.common import utc_now

def main():
    migrate_email_columns(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        bootstrap_n1(db)
    username=input('Tên đăng nhập admin: ').strip()
    full_name=input('Họ tên: ').strip()
    email=normalize_email(input('Email Admin (bắt buộc để đặt lại mật khẩu): ').strip())
    password=getpass.getpass('Mật khẩu (ít nhất 8 ký tự): ')
    confirm=getpass.getpass('Nhập lại mật khẩu: ')
    if not username or not full_name or password!=confirm:
        raise SystemExit('Thiếu thông tin hoặc hai mật khẩu không khớp.')
    try: digest=hash_password(password)
    except ValueError as e:raise SystemExit(str(e))
    with SessionLocal() as db:
        if db.scalar(select(User.id).where((User.username == username) | (User.email == email))):
            raise SystemExit('Tên đăng nhập hoặc email đã tồn tại.')
        issue_otp(db, email, 'register')
    print('Đã gửi OTP đến email Admin; kiểm tra cả Spam.')
    otp = input('Nhập OTP 6 chữ số: ').strip()
    with SessionLocal() as db:
        if db.scalar(select(User.id).where((User.username == username) | (User.email == email))):
            raise SystemExit('Tên đăng nhập hoặc email đã tồn tại.')
        consume_otp(db, email, 'register', otp)
        user=User(username=username,full_name=full_name,password_hash=digest,
                  role='admin', email=email, email_verified_at=utc_now())
        db.add(user)
        db.flush()
        attach_role_and_employee(db,user)
        db.commit()
    print('Đã tạo tài khoản admin thành công.')
if __name__=='__main__':main()
