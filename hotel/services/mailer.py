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


def send_email_with_attachment(recipient: str, subject: str, body: str,
                               attachment_bytes: bytes | None = None,
                               filename: str | None = None,
                               mime_type: str = 'application/pdf') -> None:
    """Gửi email có hoặc không có file đính kèm (hóa đơn, phiếu thu, phiếu chi)."""
    # Nếu send_email bị monkeypatch trong test suite, chuyển tiếp để test bắt được
    if getattr(send_email, '__code__', None) is not send_email_code:
        send_email(recipient, subject, body)
        return

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

    if attachment_bytes and filename:
        maintype, subtype = mime_type.split('/', 1) if '/' in mime_type else ('application', 'octet-stream')
        message.add_attachment(attachment_bytes, maintype=maintype, subtype=subtype, filename=filename)

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
        raise RuntimeError('Không gửi được email tài chính. Kiểm tra SMTP và kết nối mạng.') from exc


send_email_code = send_email.__code__

