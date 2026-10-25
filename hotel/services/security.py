from __future__ import annotations
import hashlib
import hmac
import os

# PBKDF2-HMAC-SHA256, mỗi mật khẩu có salt ngẫu nhiên riêng.
# Giữ khả năng xác thực bản ghi cũ (310_000 vòng) để nâng cấp không mất tài khoản.
PASSWORD_ITERATIONS = 600_000

def validate_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError('Mật khẩu phải có ít nhất 8 ký tự.')
    if len(password) > 1024:
        raise ValueError('Mật khẩu quá dài.')

def hash_password(password: str) -> str:
    validate_password(password)
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, PASSWORD_ITERATIONS)
    return f'pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}'

def verify_password(password: str, encoded: str) -> bool:
    try:
        alg, rounds, salt, digest = encoded.split('$')
        if alg != 'pbkdf2_sha256':
            return False
        work_factor = int(rounds)
        if not 100_000 <= work_factor <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), work_factor)
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def password_needs_rehash(encoded: str) -> bool:
    try:
        algorithm, rounds, _, _ = encoded.split('$')
        return algorithm != 'pbkdf2_sha256' or int(rounds) < PASSWORD_ITERATIONS
    except (ValueError, TypeError, AttributeError):
        return True
