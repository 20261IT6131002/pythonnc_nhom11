"""Manually verify the .env SMTP settings; never prints credentials."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from hotel.services.mailer import send_email


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    suggested = os.getenv('EMAIL_SMTP_USER', '').strip()
    recipient = input(f'Email nhận thử [{suggested}]: ').strip() or suggested
    if not recipient:
        raise SystemExit('Chưa có địa chỉ email nhận thử.')
    try:
        send_email(recipient, '[GrandStay] Kiểm tra SMTP',
                   'Kết nối SMTP GrandStay hoạt động. Bạn có thể thử gửi OTP trong ứng dụng.')
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print('Đã gửi email thử. Hãy kiểm tra Inbox/Spam của người nhận.')


if __name__ == '__main__':
    main()
