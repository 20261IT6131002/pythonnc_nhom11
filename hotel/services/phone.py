"""Consistent Vietnam phone number format for account matching.

Email OTP does NOT prove phone ownership; never treat this validation as SMS OTP.
"""
import re


def normalize_phone(value):
    digits = re.sub(r'[\s.()\-]', '', str(value or '').strip())
    if re.fullmatch(r'0[0-9]{9}', digits):
        return '+84' + digits[1:]
    if re.fullmatch(r'\+84[0-9]{9}', digits):
        return digits
    raise ValueError('Số điện thoại Việt Nam cần có 10 số bắt đầu bằng 0 (hoặc +84...).')


def phones_match(first, second):
    try:
        return normalize_phone(first) == normalize_phone(second)
    except ValueError:
        return False
