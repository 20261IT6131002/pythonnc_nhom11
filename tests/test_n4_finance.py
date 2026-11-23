"""Kiểm thử toàn diện phân hệ N4 - Tài chính & Báo cáo:
Hóa đơn, đặt cọc, thanh toán, hoàn tiền, thống kê & email.
Chạy hoàn toàn trên SQLite in-memory độc lập, không ảnh hưởng tới MySQL.
"""
import os
import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

os.environ['GRANDSTAY_TEST_MODE'] = '1'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hotel.controllers.desktop_controller import DesktopController
from hotel.models.database import Base
from hotel.models.entities import (Booking, BookingDeposit, Customer, HotelService,
                                   Invoice, Payment, Refund, Room, RoomType, User)
from hotel.services.security import hash_password
from hotel.controllers.utils import vnd


@pytest.fixture
def hotel(monkeypatch):
    outbox = []
    monkeypatch.setenv('EMAIL_OTP_SECRET', 'test-n4-secret-key-123')
    monkeypatch.setattr('hotel.services.mailer.send_email',
                        lambda recipient, subject, body: outbox.append((recipient, subject, body, None, None)))
    monkeypatch.setattr('hotel.services.mailer.send_email_with_attachment',
                        lambda recipient, subject, body, attachment_bytes=None, filename=None, mime_type='application/pdf':
                        outbox.append((recipient, subject, body, attachment_bytes, filename)))

    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False},
                           poolclass=StaticPool)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with factory() as db:
        deluxe = RoomType(name='Deluxe', capacity=3, nightly_price=Decimal('600000'))
        standard = RoomType(name='Standard', capacity=2, nightly_price=Decimal('400000'))
        db.add_all([deluxe, standard])
        db.flush()

        db.add(Room(number='201', floor=2, room_type_id=deluxe.id))
        db.add(Room(number='101', floor=1, room_type_id=standard.id))
        db.add(HotelService(name='Giặt là', price=Decimal('50000')))
        db.add(HotelService(name='Ăn sáng buffet', price=Decimal('100000')))

        db.add(User(username='admin', full_name='Admin Quản Trị',
                    password_hash=hash_password('AdminPass123'), role='admin',
                    email='admin@grandstay.local'))
        db.add(User(username='reception', full_name='Lễ Tân Ca Ngày',
                    password_hash=hash_password('StaffPass123'), role='receptionist',
                    email='letan@grandstay.local'))
        db.commit()

    c = DesktopController(factory)
    c.test_outbox = outbox
    yield c, factory
    engine.dispose()


def make_booking_data(room_id=1, name='Trần Văn Nam', phone='0912345678',
                      email='nam.tran@example.com', offset=3, nights=2):
    start = date.today() + timedelta(days=offset)
    return {
        'room_id': room_id,
        'name': name,
        'phone': phone,
        'email': email,
        'checkin': str(start),
        'checkout': str(start + timedelta(days=nights)),
        'guests': '2',
        'notes': 'Yêu cầu phòng yên tĩnh'
    }


# =====================================================================
# 1. KIỂM THỬ ĐẶT CỌC (DEPOSIT)
# =====================================================================

def test_deposit_lifecycle_and_validation(hotel, tmp_path):
    c, factory = hotel
    c.login('reception', 'StaffPass123')

    # Đặt phòng ở trạng thái pending
    data = make_booking_data(offset=5, nights=3)  # 3 đêm * 600k = 1.800.000 VND
    code = c.book(data)
    booking_row = next(r for r in c.table('bookings') if r['code'] == code)
    b_id = booking_row['id']

    # Kiểm tra số tiền cọc không hợp lệ
    with pytest.raises(ValueError, match='phải lớn hơn 0'):
        c.record_deposit(b_id, 0, 'cash')

    with pytest.raises(ValueError, match='vượt quá 150%'):
        c.record_deposit(b_id, 5000000, 'cash')  # Vượt quá giới hạn

    with pytest.raises(ValueError, match='không hợp lệ'):
        c.record_deposit(b_id, 500000, 'crypto_bitcoin')

    # Thu cọc thành công 500.000 VND qua chuyển khoản
    dep_id = c.record_deposit(b_id, 500000, 'bank_transfer', reference='MB-TX9999', notes='Cọc 30%')
    assert dep_id > 0

    # Kiểm tra email xác nhận cọc đã được gửi
    assert len(c.test_outbox) > 0
    last_mail = c.test_outbox[-1]
    assert last_mail[0] == 'nam.tran@example.com'
    assert 'Xác nhận đặt cọc' in last_mail[1]
    assert '500,000 VND' in last_mail[2]

    # Kiểm tra danh sách bảng deposits
    deposits = c.table('deposits')
    assert len(deposits) >= 1
    dep_row = next(d for d in deposits if d['code'] == code)
    assert dep_row['amount'] == vnd(500000)
    assert dep_row['method'] == 'bank_transfer'
    assert dep_row['status'] == 'Đã nhận'

    # Xuất phiếu thu tiền đặt cọc ra PDF
    dep_pdf = tmp_path / 'phieu_coc.pdf'
    c.export_deposit_receipt(dep_id, dep_pdf)
    assert dep_pdf.is_file()
    assert dep_pdf.stat().st_size > 1000


# =====================================================================
# 2. KIỂM THỬ CẤN TRỪ CỌC VÀO HÓA ĐƠN & THANH TOÁN (INVOICE & PAYMENT)
# =====================================================================

def test_deposit_deducted_from_invoice_and_checkout(hotel, tmp_path):
    c, factory = hotel
    c.login('reception', 'StaffPass123')

    # Đặt phòng 2 đêm phòng Deluxe (600k/đêm = 1.200.000 VND)
    code = c.book(make_booking_data(offset=1, nights=2))
    b_id = next(r['id'] for r in c.table('bookings') if r['code'] == code)

    # Đặt cọc 400.000 VND
    c.record_deposit(b_id, 400000, 'cash', reference='Cọc lễ tân')

    # Check in
    c.set_booking_status(b_id, 'checked_in')

    # Phát sinh dịch vụ giặt là: 50.000 VND
    service_id = c.choices('services')[0][0]
    c.add_usage(b_id, service_id, 1)

    # Chốt hóa đơn
    inv_id = c.make_invoice(b_id)
    assert inv_id > 0

    # Kiểm tra thông tin hóa đơn trên bảng
    inv_row = next(i for i in c.table('invoices') if i['code'] == code)
    # Tổng tiền: 1.200.000 (phòng) + 50.000 (dịch vụ) = 1.250.000 VND
    assert inv_row['total'] == vnd(1250000)
    assert inv_row['deposit'] == vnd(400000)
    # Còn thiếu: 1.250.000 - 400.000 = 850.000 VND
    assert inv_row['due'] == vnd(850000)

    # Kiểm tra chi tiết hóa đơn qua get_invoice_details
    details = c.get_invoice_details(inv_id)
    assert details['deposit_total'] == vnd(400000)
    assert details['due'] == vnd(850000)
    assert len(details['deposits']) == 1

    # Thử trả phòng khi chưa thanh toán đủ -> Phải bị từ chối
    with pytest.raises(ValueError, match='Cần thanh toán đủ hóa đơn trước khi trả phòng'):
        c.set_booking_status(b_id, 'checked_out')

    # Thử thanh toán vượt quá số tiền còn thiếu (vd 900.000 VND > 850.000 VND) -> Bị từ chối
    with pytest.raises(ValueError, match='không vượt số tiền còn thiếu'):
        c.pay(inv_id, 900000, 'cash')

    # Thanh toán đúng số tiền còn thiếu: 850.000 VND
    c.pay(inv_id, 850000, 'card_manual', reference='POS-4488')

    # Kiểm tra lại hóa đơn: Còn thiếu = 0 VND, trạng thái = Đã thanh toán đủ
    inv_row_after = next(i for i in c.table('invoices') if i['code'] == code)
    assert inv_row_after['due'] == vnd(0)
    assert inv_row_after['status'] == 'Đã thanh toán đủ'

    # Giờ trả phòng thành công
    c.set_booking_status(b_id, 'checked_out')
    booking_after = next(r for r in c.table('bookings') if r['code'] == code)
    assert booking_after['status'] == 'checked_out'

    # Xuất hóa đơn PDF có đầy đủ dòng cọc và thanh toán
    inv_pdf = tmp_path / f"hoa_don_{code}.pdf"
    c.export_invoice(inv_id, inv_pdf)
    assert inv_pdf.is_file()
    assert inv_pdf.stat().st_size > 1000


# =====================================================================
# 3. KIỂM THỬ HOÀN TIỀN (REFUND) THEO CHÍNH SÁCH
# =====================================================================

def test_refund_policy_and_execution(hotel, tmp_path):
    c, factory = hotel
    c.login('reception', 'StaffPass123')

    # Đơn 1: Hủy trước 5 ngày (>= 3 ngày) -> Gợi ý hoàn 100%
    code1 = c.book(make_booking_data(offset=5, nights=2))
    b1_id = next(r['id'] for r in c.table('bookings') if r['code'] == code1)
    c.record_deposit(b1_id, 600000, 'bank_transfer', reference='MB-111')

    suggest1 = c.suggest_refund(b1_id)
    assert suggest1['refundable_limit'] == Decimal('600000')
    assert suggest1['suggested_amount'] == Decimal('600000')  # 100%
    assert '≥ 3 ngày' in suggest1['policy']

    # Đơn 2: Hủy trước 1 ngày -> Gợi ý hoàn 50%
    code2 = c.book(make_booking_data(offset=1, nights=2, phone='0987654321', email='khach2@example.com'))
    b2_id = next(r['id'] for r in c.table('bookings') if r['code'] == code2)
    c.record_deposit(b2_id, 400000, 'cash')

    suggest2 = c.suggest_refund(b2_id)
    assert suggest2['refundable_limit'] == Decimal('400000')
    assert suggest2['suggested_amount'] == Decimal('200000')  # 50%
    assert '1-2 ngày' in suggest2['policy']

    # Thực hiện hoàn tiền cho đơn 1: Hoàn 600.000 VND
    ref_id = c.record_refund(b1_id, 600000, 'bank_transfer', reason='Khách hủy do bận công tác')
    assert ref_id > 0

    # Thử hoàn tiền vượt quá số tiền còn có thể hoàn -> Bị chặn
    with pytest.raises(ValueError, match='vượt quá số tiền có thể hoàn'):
        c.record_refund(b1_id, 100000, 'cash')

    # Kiểm tra bảng refunds
    refunds = c.table('refunds')
    assert len(refunds) >= 1
    ref_row = next(r for r in refunds if r['code'] == code1)
    assert ref_row['amount'] == vnd(600000)
    assert ref_row['method'] == 'bank_transfer'
    assert 'bận công tác' in ref_row['reason']

    # Xuất phiếu chi hoàn tiền PDF
    ref_pdf = tmp_path / 'phieu_chi_hoan_tien.pdf'
    c.export_refund_receipt(ref_id, ref_pdf)
    assert ref_pdf.is_file()
    assert ref_pdf.stat().st_size > 1000

    # Kiểm tra email thông báo hoàn tiền đã được gửi tới khách
    assert any('hoàn tiền' in m[1].lower() and m[0] == 'nam.tran@example.com' for m in c.test_outbox)


# =====================================================================
# 4. KIỂM THỬ EMAIL HÓA ĐƠN KÈM FILE PDF
# =====================================================================

def test_invoice_email_sending(hotel):
    c, factory = hotel
    c.login('reception', 'StaffPass123')

    # Tạo đơn và chốt hóa đơn
    code = c.book(make_booking_data(offset=1, nights=2))
    b_id = next(r['id'] for r in c.table('bookings') if r['code'] == code)
    c.set_booking_status(b_id, 'checked_in')
    inv_id = c.make_invoice(b_id)

    # Gửi hóa đơn qua email
    c.send_invoice_email(inv_id, recipient_email='nam.tran@example.com')

    # Kiểm tra outbox
    inv_emails = [m for m in c.test_outbox if 'Hóa đơn thanh toán' in m[1]]
    assert len(inv_emails) >= 1
    mail = inv_emails[-1]
    assert mail[0] == 'nam.tran@example.com'
    assert code in mail[1]
    # Phải có đính kèm PDF
    assert mail[3] is not None  # attachment bytes
    assert mail[4] == f"hoa_don_{code}.pdf"


# =====================================================================
# 5. KIỂM THỬ BÁO CÁO TÀI CHÍNH TOÀN DIỆN (STATISTICS & REPORTS)
# =====================================================================

def test_comprehensive_financial_reporting(hotel, tmp_path):
    c, factory = hotel
    today_str = str(date.today())

    # Lễ tân thực hiện các giao dịch
    c.login('reception', 'StaffPass123')

    # Giao dịch 1: Cọc 500k tiền mặt cho phòng Deluxe
    code1 = c.book(make_booking_data(room_id=1, offset=2, nights=2))
    b1_id = next(r['id'] for r in c.table('bookings') if r['code'] == code1)
    c.record_deposit(b1_id, 500000, 'cash', reference='Cọc tiền mặt')

    # Giao dịch 2: Thanh toán hóa đơn 400k chuyển khoản cho phòng Standard
    code2 = c.book(make_booking_data(room_id=2, offset=0, nights=1, phone='0933333333', email='s@test.com'))
    b2_id = next(r['id'] for r in c.table('bookings') if r['code'] == code2)
    c.set_booking_status(b2_id, 'checked_in')
    inv2_id = c.make_invoice(b2_id)
    c.pay(inv2_id, 400000, 'bank_transfer', reference='BANK-400')

    # Giao dịch 3: Hoàn tiền 150k qua chuyển khoản
    c.record_refund(b1_id, 150000, 'bank_transfer', reason='Hoàn 1 phần cọc')

    # Lễ tân xem báo cáo -> Bị từ chối vì chỉ Admin được xem báo cáo doanh thu
    with pytest.raises(PermissionError):
        c.comprehensive_financial_report(today_str, today_str)

    # Đăng nhập Admin
    c.login('admin', 'AdminPass123')
    rep = c.comprehensive_financial_report(today_str, today_str)

    # Kiểm tra các chỉ số tài chính
    assert rep['deposits_count'] >= 1
    assert rep['deposits_total'] == vnd(500000)
    assert rep['payments_count'] >= 1
    assert rep['payments_total'] == vnd(400000)
    assert rep['refunds_count'] >= 1
    assert rep['refunds_total'] == vnd(150000)

    # Tổng thực thu Gross = 500k + 400k = 900k
    assert rep['gross_revenue'] == vnd(900000)
    # Doanh thu thuần Net = Gross (900k) - Refund (150k) = 750k
    assert rep['net_revenue'] == vnd(750000)

    # Kiểm tra phân bổ phương thức
    cash_method = next(m for m in rep['methods'] if m['name'] == 'Tiền mặt')
    assert cash_method['deposit'] == vnd(500000)

    bank_method = next(m for m in rep['methods'] if m['name'] == 'Chuyển khoản')
    assert bank_method['payment'] == vnd(400000)
    assert bank_method['refund'] == vnd(150000)

    # Kiểm tra danh sách giao dịch chi tiết
    assert len(rep['transactions']) >= 3

    # Xuất PDF Báo cáo tài chính toàn diện
    report_pdf = tmp_path / 'bao_cao_tai_chinh_toan_dien.pdf'
    c.export_comprehensive_financial_report(today_str, today_str, report_pdf)
    assert report_pdf.is_file()
    assert report_pdf.stat().st_size > 1500


# =====================================================================
# 6. KIỂM THỬ KHÁCH HÀNG TRA CỨU & TẢI HÓA ĐƠN
# =====================================================================

def test_customer_lookup_finance_info(hotel, tmp_path):
    c, factory = hotel

    # Staff lập đơn, nhận cọc và chốt hóa đơn
    c.login('reception', 'StaffPass123')
    code = c.book(make_booking_data(offset=1, nights=2))
    b_id = next(r['id'] for r in c.table('bookings') if r['code'] == code)
    c.record_deposit(b_id, 300000, 'cash')
    c.set_booking_status(b_id, 'checked_in')
    inv_id = c.make_invoice(b_id)

    # Đăng xuất nhân viên -> Thành khách vãng lai
    c.user = None

    # Khách tra cứu bằng mã và số điện thoại
    info = c.lookup(code, '0912345678')
    assert info['code'] == code
    assert info['deposit'] == vnd(300000)
    assert info['has_invoice'] is True
    assert info['invoice_id'] == inv_id
    assert info['due'] == vnd(900000)  # 1.200.000 - 300.000 = 900.000 VND

    # Khách tải hóa đơn PDF của đơn này
    cust_pdf = tmp_path / f"khach_tai_hoa_don_{code}.pdf"
    c.export_invoice(inv_id, cust_pdf)
    assert cust_pdf.is_file()
    assert cust_pdf.stat().st_size > 1000
