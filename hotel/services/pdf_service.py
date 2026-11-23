from __future__ import annotations
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# Không nhúng font hệ thống vào ZIP; khi chạy tìm font Unicode của máy người dùng.
def _font_name():
    candidates = [
        Path('C:/Windows/Fonts/arial.ttf'), Path('C:/Windows/Fonts/tahoma.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'),
    ]
    for font_path in candidates:
        if font_path.is_file():
            try:
                if 'HotelUnicode' not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont('HotelUnicode', str(font_path)))
                return 'HotelUnicode'
            except Exception:
                continue
    raise RuntimeError('Không tìm thấy font Unicode cho PDF. Cần Arial hoặc Tahoma trên Windows.')

def _build(title, headers, rows, footers=()):
    font=_font_name()
    out=BytesIO()
    doc=SimpleDocTemplate(out,pagesize=(210*mm,297*mm),leftMargin=17*mm,rightMargin=17*mm,topMargin=20*mm,bottomMargin=18*mm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='HotelTitle',fontName=font,fontSize=17,leading=25,alignment=TA_CENTER,spaceAfter=13))
    styles.add(ParagraphStyle(name='HotelCell',fontName=font,fontSize=9,leading=13))
    elems=[Paragraph(title,styles['HotelTitle']),Spacer(1,5*mm)]
    table=Table([[Paragraph(escape(str(x)),styles['HotelCell']) for x in row]
                 for row in [headers]+list(rows)],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfebf5')),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#cad6e0')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    elems.append(table)
    for text in footers:
        elems.append(Spacer(1,4*mm))
        elems.append(Paragraph(escape(str(text)),styles['HotelCell']))
    doc.build(elems)
    out.seek(0)
    return out.getvalue()

def invoice_pdf(invoice, customer_snapshot=None):
    b = invoice.booking
    customer = customer_snapshot or b.customer
    rows = [
        ('Khách hàng', customer.full_name),
        ('Mã đặt phòng', b.code),
        ('Phòng', b.room.number),
        ('Ngày nhận / trả', f'{b.checkin_date:%d/%m/%Y} - {b.checkout_date:%d/%m/%Y}'),
        ('Tiền phòng', f'{invoice.room_amount:,.0f} VND')
    ]
    for u in b.usages:
        rows.append((f'{u.service.name} x {u.quantity}', f'{u.unit_price * u.quantity:,.0f} VND'))
    rows.append(('Tiền dịch vụ', f'{invoice.services_amount:,.0f} VND'))
    if invoice.discount_amount:
        rows.append(('Khuyến mãi', f'-{invoice.discount_amount:,.0f} VND'))
    rows.append(('TỔNG CỘNG', f'{invoice.total_amount:,.0f} VND'))

    paid = sum(p.amount for p in invoice.payments)
    deposits = sum(d.amount for d in b.deposits if d.status in ('paid', 'applied')) if getattr(b, 'deposits', None) else 0
    refunds = sum(r.amount for r in b.refunds if r.status == 'completed') if getattr(b, 'refunds', None) else 0

    if deposits:
        rows.append(('Đã đặt cọc (khấu trừ)', f'-{deposits:,.0f} VND'))
    if paid:
        rows.append(('Đã thanh toán thêm', f'-{paid:,.0f} VND'))
    if refunds:
        rows.append(('Đã hoàn tiền', f'+{refunds:,.0f} VND'))

    net_paid = max(0, paid + deposits - refunds)
    due = max(0, invoice.total_amount - net_paid)
    status_label = 'ĐÃ THANH TOÁN ĐỦ' if due == 0 else f'CÒN THIẾU: {due:,.0f} VND'

    return _build('HÓA ĐƠN KHÁCH SẠN - GRANDSTAY',
                  ('Nội dung', 'Thông tin'), rows, [
                      f'Tổng đã đóng (gồm cọc): {net_paid:,.0f} VND',
                      f'Tình trạng: {status_label}',
                      'Chứng từ do hệ thống tạo; không phải hóa đơn điện tử thuế.'
                  ])


def deposit_receipt_pdf(deposit, booking):
    method_name = {'cash': 'Tiền mặt', 'bank_transfer': 'Chuyển khoản', 'card_manual': 'Thẻ'}.get(deposit.method, deposit.method)
    recorder_name = deposit.recorder.full_name if deposit.recorder else 'Lễ tân'
    rows = [
        ('Mã phiếu thu', f"DEP-{deposit.id}"),
        ('Mã đặt phòng', booking.code),
        ('Khách hàng', booking.customer.full_name if booking.customer else '-'),
        ('Số điện thoại', booking.customer.phone if booking.customer else '-'),
        ('Phòng', f"Phòng {booking.room.number} ({booking.room.room_type.name})"),
        ('Thời gian lưu trú', f"{booking.checkin_date:%d/%m/%Y} → {booking.checkout_date:%d/%m/%Y}"),
        ('SỐ TIỀN ĐẶT CỌC', f"{deposit.amount:,.0f} VND"),
        ('Phương thức thu', method_name),
        ('Mã giao dịch / Ghi chú', deposit.reference or deposit.notes or 'Không có'),
        ('Thời gian lập phiếu', deposit.created_at.strftime('%d/%m/%Y %H:%M')),
        ('Người thu tiền', recorder_name),
    ]
    return _build('PHIẾU THU TIỀN ĐẶT CỌC - GRANDSTAY',
                  ('Khoản mục', 'Chi tiết'), rows, [
                      f'Số tiền bằng số: {deposit.amount:,.0f} VND',
                      'Khoản tiền cọc này sẽ được trừ trực tiếp vào hóa đơn thanh toán khi trả phòng.',
                      'GrandStay Hotel & Resort xin trân trọng cảm ơn Quý khách!'
                  ])


def refund_receipt_pdf(refund, booking):
    method_name = {'cash': 'Tiền mặt', 'bank_transfer': 'Chuyển khoản', 'card_manual': 'Thẻ'}.get(refund.method, refund.method)
    recorder_name = refund.recorder.full_name if refund.recorder else 'Nhân viên quản lý'
    rows = [
        ('Mã phiếu chi', f"REF-{refund.id}"),
        ('Mã đặt phòng', booking.code),
        ('Khách hàng', booking.customer.full_name if booking.customer else '-'),
        ('Số điện thoại', booking.customer.phone if booking.customer else '-'),
        ('Phòng liên quan', f"Phòng {booking.room.number}"),
        ('SỐ TIỀN HOÀN LẠI', f"{refund.amount:,.0f} VND"),
        ('Phương thức chi', method_name),
        ('Lý do hoàn tiền', refund.reason or 'Hoàn tiền theo chính sách khách sạn'),
        ('Thời gian xử lý', refund.created_at.strftime('%d/%m/%Y %H:%M')),
        ('Người lập phiếu chi', recorder_name),
    ]
    return _build('PHIẾU CHI HOÀN TIỀN - GRANDSTAY',
                  ('Khoản mục', 'Chi tiết'), rows, [
                      f'Số tiền hoàn lại: {refund.amount:,.0f} VND',
                      'Giao dịch hoàn tiền đã được ghi nhận vào sổ quỹ của khách sạn.',
                      'GrandStay Hotel & Resort trân trọng cảm ơn sự thông cảm của Quý khách!'
                  ])


def comprehensive_report_pdf(start, end, report):
    rows = [
        ('Kỳ báo cáo', f"{start:%d/%m/%Y} đến {end:%d/%m/%Y}"),
        ('Tiền thanh toán hóa đơn', f"{report['payments_total']:,.0f} VND ({report['payments_count']} GD)"),
        ('Tiền đặt cọc nhận vào', f"{report['deposits_total']:,.0f} VND ({report['deposits_count']} GD)"),
        ('TỔNG TIỀN THỰC THU (GROSS)', f"{report['gross_revenue']:,.0f} VND"),
        ('Tiền đã hoàn lại cho khách', f"-{report['refunds_total']:,.0f} VND ({report['refunds_count']} GD)"),
        ('DOANH THU THUẦN (NET REVENUE)', f"{report['net_revenue']:,.0f} VND"),
        ('Tổng giá trị hóa đơn trong kỳ', f"{report['total_invoice_amount']:,.0f} VND ({report['invoices_count']} HĐ)"),
        ('Công nợ còn phải thu (Due)', f"{report['total_due']:,.0f} VND"),
    ]
    for method_key, m in report.get('methods', {}).items():
        rows.append((f"Phương thức: {m['name']}", f"Thu: {m['payment'] + m['deposit']:,.0f} | Hoàn: {m['refund']:,.0f} | Thuần: {m['net']:,.0f} VND"))

    footers = [
        f"Doanh thu thuần thực tế sau hoàn tiền: {report['net_revenue']:,.0f} VND",
        "Báo cáo tài chính nội bộ GrandStay Hotel & Resort.",
        "Người xuất báo cáo: Quản trị viên (Admin) hệ thống."
    ]
    return _build('BÁO CÁO TÀI CHÍNH TOÀN DIỆN - GRANDSTAY',
                  ('Chỉ số tài chính', 'Giá trị ghi nhận'), rows, footers)


def report_pdf(start,end,payments,total):
    rows=[(str(p.id),p.created_at.strftime('%d/%m/%Y'),p.invoice.booking.code,f'{p.amount:,.0f} VND') for p in payments]
    if not rows: rows=[('-','-','Không có giao dịch','0 VND')]
    return _build('BÁO CÁO DOANH THU - GRANDSTAY',('Mã TT','Ngày','Mã đặt phòng','Số tiền'),rows,[f'Kỳ báo cáo: {start:%d/%m/%Y} - {end:%d/%m/%Y}',f'Tổng tiền đã ghi nhận: {total:,.0f} VND'])
