"""Kiểm tra cấu hình độc lập; tuyệt đối không kết nối MySQL thật."""
import pytest
from sqlalchemy.engine import make_url


@pytest.fixture
def make_config(monkeypatch):
    # Cho phép import config khi chạy riêng file test mà không cần .env hay MySQL.
    monkeypatch.setenv('GRANDSTAY_TEST_MODE', '1')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    from hotel.config import build_database_url
    return build_database_url


def test_empty_password_and_database_name(make_config):
    dsn = make_config({
        'MYSQL_HOST': '127.0.0.1', 'MYSQL_PORT': '3306',
        'MYSQL_USER': 'root', 'MYSQL_PASSWORD': '',
        'MYSQL_DATABASE': 'grandstay_nhom11',
    })
    url = make_url(dsn)
    assert url.drivername == 'mysql+pymysql'
    assert url.username == 'root'
    assert url.password == ''
    assert url.host == '127.0.0.1'
    assert url.database == 'grandstay_nhom11'


def test_special_characters_in_mysql_password(make_config):
    secret = 'a@b#c:/%d'
    dsn = make_config({
        'MYSQL_HOST': 'localhost', 'MYSQL_PORT': '3307',
        'MYSQL_USER': 'grandstay_app', 'MYSQL_PASSWORD': secret,
        'MYSQL_DATABASE': 'grandstay_nhom11',
    })
    url = make_url(dsn)
    assert url.password == secret
    assert url.host == 'localhost'
    assert url.port == 3307
    assert '@localhost' not in url.host


def test_mysql_fields_take_priority_over_old_database_url(make_config):
    dsn = make_config({
        'DATABASE_URL': 'mysql+pymysql://wrong:wrong@badhost/old_db',
        'MYSQL_USER': 'root', 'MYSQL_PASSWORD': '',
        'MYSQL_DATABASE': 'grandstay_nhom11',
    })
    assert make_url(dsn).database == 'grandstay_nhom11'


def test_sqlite_test_compatibility(make_config):
    assert make_config({
        'GRANDSTAY_TEST_MODE': '1',
        'DATABASE_URL': 'sqlite:///:memory:',
        'MYSQL_DATABASE': 'not_used',
    }) == 'sqlite:///:memory:'


@pytest.mark.parametrize('port', ['abc', '0', '65536'])
def test_invalid_port_has_clear_message(make_config, port):
    with pytest.raises(RuntimeError, match='MYSQL_PORT'):
        make_config({'MYSQL_DATABASE': 'grandstay_nhom11', 'MYSQL_PORT': port})
