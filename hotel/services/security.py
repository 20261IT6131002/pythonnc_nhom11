from __future__ import annotations
import hashlib
import hmac
import os

def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError('Mật khẩu phải có ít nhất 8 ký tự.')
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310000)
    return f'pbkdf2_sha256$310000${salt.hex()}${digest.hex()}'

def verify_password(password: str, encoded: str) -> bool:
    try:
        alg, rounds, salt, digest = encoded.split('$')
        if alg != 'pbkdf2_sha256':
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False
