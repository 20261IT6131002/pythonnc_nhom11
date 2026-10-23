"""Cấu hình MySQL lấy từ .env; ưu tiên các biến MYSQL_* dễ chỉnh sửa."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')


def build_database_url(settings=None):
    """Hỗ trợ MYSQL_*; vẫn tương thích DATABASE_URL cũ và SQLite khi test."""
    values = os.environ if settings is None else settings
    legacy_url = values.get('DATABASE_URL', '').strip()
    test_mode = values.get('GRANDSTAY_TEST_MODE') == '1'

    # Test có thể dùng SQLite trong bộ nhớ, không bao giờ kết nối MySQL thật.
    if test_mode and legacy_url:
        return legacy_url

    mysql_fields = ('MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER',
                    'MYSQL_PASSWORD', 'MYSQL_DATABASE')
    if any(key in values for key in mysql_fields):
        host = values.get('MYSQL_HOST', '127.0.0.1').strip()
        username = values.get('MYSQL_USER', 'root').strip()
        password = values.get('MYSQL_PASSWORD', '')
        database = values.get('MYSQL_DATABASE', '').strip()
        port_text = values.get('MYSQL_PORT', '3306').strip()
        if not host or not username or not database:
            raise RuntimeError('Cần điền MYSQL_HOST, MYSQL_USER và MYSQL_DATABASE trong .env.')
        try:
            port = int(port_text)
        except ValueError as exc:
            raise RuntimeError('MYSQL_PORT phải là số nguyên, ví dụ 3306.') from exc
        if not 1 <= port <= 65535:
            raise RuntimeError('MYSQL_PORT phải nằm trong khoảng 1..65535.')

        # URL.create tự mã hóa mật khẩu có @, #, /, : hoặc %.
        return URL.create(
            'mysql+pymysql', username=username, password=password,
            host=host, port=port, database=database,
            query={'charset': 'utf8mb4'},
        ).render_as_string(hide_password=False)

    if legacy_url:
        if not test_mode and not legacy_url.startswith('mysql+pymysql://'):
            raise RuntimeError('Bản desktop yêu cầu MySQL; không dùng SQLite khi vận hành.')
        return legacy_url
    raise RuntimeError('Chưa cấu hình MySQL. Sao chép .env.example thành .env.')


DATABASE_URL = build_database_url()
