"""Offline recovery for the database operator when the only Admin forgot a password.

Run interactively on a trusted computer with a configured .env and MySQL access.
No default password or insecure reset link is generated.
"""
from __future__ import annotations

import getpass

from sqlalchemy import select

from hotel.models.database import SessionLocal, engine, Base
from hotel.services.email_schema import migrate_email_columns
from hotel.models.entities import User
from hotel.services.business import log_event
from hotel.services.security import hash_password


def main():
    migrate_email_columns(engine)
    Base.metadata.create_all(engine)
    print('Khôi phục tài khoản (chỉ chạy bởi người quản trị cơ sở dữ liệu).')
    username = input('Tên đăng nhập cần khôi phục: ').strip()
    if not username:
        raise SystemExit('Cần nhập tên đăng nhập.')
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            raise SystemExit('Không tồn tại tài khoản này.')
        answer = input(f'Đặt lại mật khẩu cho {user.username} ({user.role})? Gõ YES: ')
        if answer != 'YES':
            raise SystemExit('Đã hủy.')
        password = getpass.getpass('Mật khẩu mới: ')
        confirmation = getpass.getpass('Nhập lại mật khẩu: ')
        if password != confirmation:
            raise SystemExit('Mật khẩu xác nhận không khớp.')
        try:
            user.password_hash = hash_password(password)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        log_event(db, None, 'auth.offline_reset', user.username)
        db.commit()
    print('Đã đặt lại mật khẩu. Không có mật khẩu nào được in ra màn hình.')


if __name__ == '__main__':
    main()
