"""SMTP delivery for GrandStay verification emails.

SMTP passwords come only from .env / process environment, never from source code.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def send_email(recipient: str, subject: str, body: str) -> None:
    host = os.getenv('EMAIL_SMTP_HOST', '').strip()
    port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
    username = os.getenv('EMAIL_SMTP_USER', '').strip()
    password = os.getenv('EMAIL_SMTP_PASSWORD', '')
    sender = os.getenv('EMAIL_FROM', '').strip() or username
    security = os.getenv('EMAIL_SMTP_SECURITY', 'starttls').lower().strip()
    if not all((host, username, password, sender)):
        raise RuntimeError('Chưa cấu hình EMAIL_SMTP_HOST/USER/PASSWORD/FROM trong .env.')
    if security not in ('starttls', 'ssl'):
        raise RuntimeError('EMAIL_SMTP_SECURITY phải là starttls hoặc ssl.')
    if any('\n' in s or '\r' in s for s in (recipient, subject, sender)):
        raise ValueError('Địa chỉ email hoặc tiêu đề không hợp lệ.')

    message = EmailMessage()
    message['From'] = sender
    message['To'] = recipient
    message['Subject'] = subject
    message.set_content(body)
    try:
        context = ssl.create_default_context()
        if security == 'ssl':
            with smtplib.SMTP_SSL(host, port, timeout=12, context=context) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=12) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise RuntimeError('Không gửi được email OTP. Kiểm tra SMTP, mật khẩu ứng dụng và kết nối Internet.') from exc
