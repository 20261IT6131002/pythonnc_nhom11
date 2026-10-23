"""Tạo Admin đầu tiên bằng CLI. Không đặt tài khoản/mật khẩu mặc định trong mã nguồn."""
from __future__ import annotations
import getpass
from sqlalchemy import select
from hotel.models.database import Base,engine,SessionLocal
from hotel.models.entities import User
from hotel.services.security import hash_password

def main():
    Base.metadata.create_all(engine)
    username=input('Tên đăng nhập admin: ').strip()
    full_name=input('Họ tên: ').strip()
    password=getpass.getpass('Mật khẩu (ít nhất 8 ký tự): ')
    confirm=getpass.getpass('Nhập lại mật khẩu: ')
    if not username or not full_name or password!=confirm:
        raise SystemExit('Thiếu thông tin hoặc hai mật khẩu không khớp.')
    try: digest=hash_password(password)
    except ValueError as e:raise SystemExit(str(e))
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.username==username)):
            raise SystemExit('Tên đăng nhập đã tồn tại.')
        db.add(User(username=username,full_name=full_name,password_hash=digest,role='admin'))
        db.commit()
    print('Đã tạo tài khoản admin thành công.')
if __name__=='__main__':main()
