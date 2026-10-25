"""Time-limited, single-use email OTP verification.

Never persist or log the plain OTP.  Six digits are kept practical for users,
with a short expiry, resend cooldown and five verification attempts.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import timedelta

from sqlalchemy import select

from hotel.models.entities import EmailOtp
from hotel.models.common import utc_now
from hotel.services import mailer


OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_SECONDS = 60
_PROCESS_SECRET = secrets.token_bytes(32)


def normalize_email(value: str) -> str:
    email = str(value).strip().lower()
    if len(email) > 254 or not re.fullmatch(r'[^@\s\x00-\x1f]+@[^@\s\x00-\x1f]+\.[a-z0-9-]{2,63}', email):
        raise ValueError('Địa chỉ email không hợp lệ.')
    return email


def _digest(email: str, purpose: str, code: str, salt: str) -> str:
    configured = os.getenv('EMAIL_OTP_SECRET', '')
    key = configured.encode('utf-8') if configured else _PROCESS_SECRET
    payload = f'{purpose}:{email}:{salt}:{code}'.encode('utf-8')
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def issue_otp(db, email: str, purpose: str) -> None:
    if purpose not in {'register', 'reset', 'link', 'guest_booking'}:
        raise ValueError('Mục đích xác minh email không hợp lệ.')
    email = normalize_email(email)
    now = utc_now()
    last = db.scalar(select(EmailOtp).where(EmailOtp.email == email,
                                          EmailOtp.purpose == purpose)
                     .order_by(EmailOtp.id.desc()).limit(1))
    if last and (now - last.issued_at).total_seconds() < OTP_RESEND_SECONDS:
        raise ValueError('Vui lòng đợi 60 giây trước khi gửi lại OTP.')

    code = f'{secrets.randbelow(1_000_000):06d}'
    salt = secrets.token_hex(16)
    subject = '[GrandStay] Mã xác minh email'
    body = (f'Mã OTP GrandStay của bạn: {code}\n'
            f'Mục đích: {purpose}\n'
            f'Mã có hiệu lực {OTP_TTL_MINUTES} phút và chỉ sử dụng một lần.\n'
            'Nếu bạn không yêu cầu, hãy bỏ qua email này.\n'
            'Không cung cấp mã OTP cho bất kỳ ai.')
    # Only persist a usable code after the SMTP provider accepted the message.
    mailer.send_email(email, subject, body)
    if last and last.used_at is None:
        last.used_at = now
    db.add(EmailOtp(email=email, purpose=purpose,
                    salt=salt, code_digest=_digest(email, purpose, code, salt),
                    issued_at=now, expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
                    attempts=0))
    db.commit()


def consume_otp(db, email: str, purpose: str, code: str) -> None:
    email = normalize_email(email)
    now = utc_now()
    token = db.scalar(select(EmailOtp).where(EmailOtp.email == email,
                    EmailOtp.purpose == purpose, EmailOtp.used_at.is_(None))
                    .order_by(EmailOtp.id.desc()).limit(1))
    if (not token or token.expires_at <= now or
            token.attempts >= OTP_MAX_ATTEMPTS or
            not re.fullmatch(r'\d{6}', str(code).strip())):
        raise ValueError('OTP không hợp lệ, đã hết hạn hoặc đã bị khóa.')
    expected = _digest(email, purpose, str(code).strip(), token.salt)
    if not hmac.compare_digest(expected, token.code_digest):
        token.attempts += 1
        db.commit()  # Preserve failed attempts despite the controller raising.
        raise ValueError('OTP không đúng. Hãy kiểm tra email và thử lại.')
    token.used_at = now
