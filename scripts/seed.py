"""Dữ liệu mẫu an toàn: không xóa dữ liệu thật; chỉ tạo khi chưa tồn tại."""
from sqlalchemy import select
from hotel.models.database import engine, SessionLocal, Base
from hotel.models.entities import Room,RoomType,HotelService
from decimal import Decimal

def run():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(RoomType.id).limit(1)):
            print('Đã có dữ liệu loại phòng; không nạp lặp.');return
        types=[RoomType(name='Standard',nightly_price=Decimal('350000'),capacity=2,description='Phòng tiêu chuẩn đầy đủ tiện nghi.'),
               RoomType(name='Deluxe',nightly_price=Decimal('600000'),capacity=3,description='Không gian rộng rãi, thoải mái.'),
               RoomType(name='VIP Suite',nightly_price=Decimal('1200000'),capacity=4,description='Không gian cao cấp cho kỳ nghỉ đặc biệt.')]
        db.add_all(types);db.flush()
        for number,typ in [('101',0),('102',0),('201',1),('202',1),('301',2)]:
            db.add(Room(number=number,floor=int(number[0]),room_type_id=types[typ].id))
        db.add_all([HotelService(name='Ăn uống',price=Decimal('200000')),HotelService(name='Giặt là',price=Decimal('50000')),HotelService(name='Đưa đón',price=Decimal('150000'))])
        db.commit();print('Đã tạo 3 loại phòng, 5 phòng và 3 dịch vụ mẫu.')
if __name__=='__main__':run()
