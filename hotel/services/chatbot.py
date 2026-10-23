from __future__ import annotations
import re
from datetime import date
from sqlalchemy import select
from hotel.models.entities import RoomType, HotelService
from hotel.services.business import find_rooms

def reply(db, message: str) -> str:
    """Chatbot theo quy tắc, đọc dữ liệu thật; không sử dụng AI API ngoài."""
    q = message.lower().strip()
    if len(q) > 500:
        return 'Bạn vui lòng gửi câu hỏi ngắn hơn (dưới 500 ký tự).'
    if any(x in q for x in ('xin chào','hello','chào','hi ')):
        return 'Xin chào! Mình có thể tư vấn loại phòng, giá, dịch vụ và tình trạng phòng theo ngày. Bạn muốn tìm hiểu gì?'
    if any(x in q for x in ('trống', 'còn phòng', 'phòng nào', 'available')):
        matches = re.findall(r'\d{4}-\d{2}-\d{2}', q)
        if len(matches) < 2:
            return 'Để kiểm tra phòng trống chính xác, vui lòng nhập hai ngày theo dạng YYYY-MM-DD. Ví dụ: "Còn phòng 2026-11-01 2026-11-03 không?"'
        try:
            checkin,checkout=(date.fromisoformat(matches[0]),date.fromisoformat(matches[1]))
            rooms=find_rooms(db,checkin,checkout)
        except ValueError as exc:
            return str(exc)
        if not rooms:
            return 'Hiện không có phòng phù hợp trong khoảng ngày bạn yêu cầu.'
        shown=', '.join(f'{r.number} ({r.room_type.name})' for r in rooms[:8])
        return f'Các phòng trống từ {checkin:%d/%m/%Y} đến {checkout:%d/%m/%Y}: {shown}.' + (' Và một số phòng khác.' if len(rooms)>8 else '')
    if any(x in q for x in ('giá','bao nhiêu','loại phòng','phòng vip','phòng deluxe','phòng standard')):
        rows=db.scalars(select(RoomType).order_by(RoomType.nightly_price)).all()
        if not rows: return 'Hiện chưa có bảng giá phòng.'
        return 'Bảng giá hiện tại: ' + '; '.join(f'{r.name}: {r.nightly_price:,.0f}đ/đêm (tối đa {r.capacity} khách)' for r in rows) + '. Giá thực tế được chốt khi đặt phòng.'
    if any(x in q for x in ('dịch vụ', 'ăn uống', 'giặt', 'spa', 'đưa đón')):
        rows=db.scalars(select(HotelService).where(HotelService.active.is_(True)).order_by(HotelService.name)).all()
        return ('Các dịch vụ: '+ '; '.join(f'{s.name} ({s.price:,.0f}đ)' for s in rows)+'.') if rows else 'Khách sạn chưa khai báo dịch vụ.'
    if any(x in q for x in ('đặt phòng','booking','đặt như thế nào','đặt thế nào')):
        return 'Bạn vào mục Phòng nghỉ, chọn ngày nhận/trả phòng, chọn phòng trống rồi điền thông tin liên hệ. Sau khi gửi, bạn nhận mã đặt phòng để tra cứu. Lễ tân sẽ xác nhận đơn.'
    if any(x in q for x in ('hủy', 'huỷ', 'đổi ngày')):
        return 'Để thay đổi hoặc hủy đơn đã đặt, vui lòng liên hệ lễ tân và cung cấp mã đặt phòng cùng số điện thoại xác minh.'
    return 'Mình hỗ trợ tư vấn giá phòng, dịch vụ, kiểm tra phòng trống theo ngày và hướng dẫn đặt phòng. Bạn thử hỏi: "Giá phòng Deluxe bao nhiêu?"'
