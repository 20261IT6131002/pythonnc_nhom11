"""Read-only verification of the exact MySQL schema GrandStay is using.

Run: .\.venv\Scripts\python.exe -m scripts.verify_mysql_accounts
Optional: .\.venv\Scripts\python.exe -m scripts.verify_mysql_accounts --username letan

Never prints database passwords or user password hashes.
"""
from __future__ import annotations

import argparse

from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

from hotel.config import DATABASE_URL
from hotel.models.database import SessionLocal, engine
from hotel.models.entities import Employee, User


def main():
    parser = argparse.ArgumentParser(description='Kiểm tra MySQL GrandStay không sửa dữ liệu')
    parser.add_argument('--username', help='Chỉ kiểm tra tên đăng nhập này')
    args = parser.parse_args()
    parsed = make_url(DATABASE_URL)
    if not parsed.drivername.startswith('mysql'):
        raise RuntimeError('Ứng dụng không cấu hình MySQL; hãy kiểm tra .env và biến môi trường.')

    print('=== MYSQL CỦA ỨNG DỤNG GRANDSTAY ===')
    print(f'Host: {parsed.host}:{parsed.port or 3306}')
    print(f'Database trong cấu hình: {parsed.database}')
    print(f'Tài khoản kết nối MySQL: {parsed.username}')
    with engine.connect() as conn:
        print(f'Database đang kết nối thực tế: {conn.execute(text("SELECT DATABASE() ")).scalar()}')
        names = set(inspect(conn).get_table_names())
        expected = {'users', 'employees', 'user_roles', 'customers'}
        missing = sorted(expected - names)
        if missing:
            print(f'THIẾU BẢNG: {", ".join(missing)}. Hãy khởi động main.py để tạo bảng.')
            return 1

    with SessionLocal() as db:
        print(f'Tổng tài khoản trong users: {db.scalar(select(func.count(User.id)))}')
        print(f'Tổng hồ sơ nhân viên trong employees: {db.scalar(select(func.count(Employee.id)))}')
        statement = select(User).order_by(User.id.desc()).limit(20)
        if args.username:
            statement = select(User).where(User.username == args.username).limit(1)
        users = db.scalars(statement).all()
        if not users:
            print('Không tìm thấy tên đăng nhập trong database được chỉ ra ở trên.')
        for account in users:
            print(f'  ID={account.id} | {account.username} | {account.role} | '
                  f'active={account.active} | deleted_soft={account.archived_at is not None} | '
                  f'email={"có" if account.email else "chưa có"}')
    print('So sánh tên Database ở trên với schema đang mở trong MySQL Workbench.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
