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

def invoice_pdf(invoice):
    b=invoice.booking
    rows=[('Khách hàng', b.customer.full_name),('Mã đặt phòng',b.code),('Phòng',b.room.number),('Ngày nhận / trả',f'{b.checkin_date:%d/%m/%Y} - {b.checkout_date:%d/%m/%Y}'),('Tiền phòng',f'{invoice.room_amount:,.0f} VND')]
    for u in b.usages:
        rows.append((f'{u.service.name} x {u.quantity}',f'{u.unit_price * u.quantity:,.0f} VND'))
    rows.extend([('Tiền dịch vụ',f'{invoice.services_amount:,.0f} VND'),('TỔNG CỘNG',f'{invoice.total_amount:,.0f} VND')])
    paid=sum(p.amount for p in invoice.payments)
    return _build('HÓA ĐƠN KHÁCH SẠN - GRANDSTAY',('Nội dung','Thông tin'),rows,[f'Đã thanh toán: {paid:,.0f} VND', f'Còn thiếu: {max(0,invoice.total_amount-paid):,.0f} VND','Chứng từ do hệ thống tạo; không phải hóa đơn điện tử thuế.'])

def report_pdf(start,end,payments,total):
    rows=[(str(p.id),p.created_at.strftime('%d/%m/%Y'),p.invoice.booking.code,f'{p.amount:,.0f} VND') for p in payments]
    if not rows: rows=[('-','-','Không có giao dịch','0 VND')]
    return _build('BÁO CÁO DOANH THU - GRANDSTAY',('Mã TT','Ngày','Mã đặt phòng','Số tiền'),rows,[f'Kỳ báo cáo: {start:%d/%m/%Y} - {end:%d/%m/%Y}',f'Tổng tiền đã ghi nhận: {total:,.0f} VND'])
