"""Tên trang, mô tả và cấu hình cột của các bảng quản trị GrandStay."""

TAB_NAMES = {
    'dashboard': 'Tổng quan', 'types': 'Loại phòng & giá', 'rooms': 'Phòng',
    'customers': 'Khách hàng', 'bookings': 'Đặt / nhận / trả phòng',
    'calendar': 'Lịch phòng', 'services': 'Dịch vụ', 'invoices': 'Hóa đơn',
    'reports': 'Thống kê doanh thu', 'chat': 'Tư vấn tự động',
    'users': 'Nhân viên', 'logs': 'Nhật ký',
}

TABLE_COLUMNS = {
    'types': [('id', 'ID', 50), ('name', 'Loại phòng', 180), ('capacity', 'Sức chứa', 100),
              ('price', 'Giá / đêm (VND)', 160), ('description', 'Mô tả', 330)],
    'rooms': [('id', 'ID', 50), ('number', 'Số phòng', 100), ('type', 'Loại', 180),
              ('floor', 'Tầng', 65), ('price', 'Giá / đêm (VND)', 150), ('active', 'Hoạt động', 110)],
    'customers': [('id', 'ID', 50), ('name', 'Khách hàng', 200), ('phone', 'SĐT', 140),
                  ('email', 'Email', 200), ('document_no', 'CCCD / Hộ chiếu', 180)],
    'bookings': [('id', 'ID', 50), ('code', 'Mã đặt', 160), ('customer', 'Khách hàng', 170),
                 ('phone', 'SĐT', 120), ('room', 'Phòng', 75), ('checkin', 'Ngày nhận', 115),
                 ('checkout', 'Ngày trả', 115), ('status', 'Trạng thái', 115),
                 ('estimate', 'Tiền phòng dự kiến', 180)],
    'services': [('id', 'ID', 50), ('name', 'Dịch vụ', 210),
                 ('price', 'Giá (VND)', 170), ('active', 'Đang bán', 110)],
    'invoices': [('id', 'ID', 60), ('code', 'Mã đặt', 160), ('customer', 'Khách', 160),
                 ('room', 'Phòng', 150), ('services', 'Dịch vụ', 150),
                 ('total', 'Tổng cộng', 150), ('paid', 'Đã thu', 150), ('due', 'Còn thiếu', 150)],
    'users': [('id', 'ID', 50), ('username', 'Tài khoản', 155),
              ('name', 'Họ tên', 210), ('role', 'Vai trò', 140), ('active', 'Hoạt động', 120)],
    'logs': [('id', 'ID', 60), ('date', 'Thời gian', 210), ('actor', 'Người thao tác', 130),
             ('action', 'Hành động', 190), ('details', 'Chi tiết', 300)],
}

PAGE_DESCRIPTIONS = {
    'dashboard': 'Theo dõi tình hình đặt phòng và hoạt động khách sạn.',
    'types': 'Quản lý danh mục loại phòng, bảng giá và sức chứa.',
    'rooms': 'Thông tin phòng, loại, giá và tình trạng vận hành.',
    'customers': 'Hồ sơ khách hàng và lịch sử đặt phòng.',
    'bookings': 'Xác nhận yêu cầu, nhận phòng và trả phòng.',
    'calendar': 'Theo dõi lịch giữ phòng và tình trạng theo ngày.',
    'services': 'Dịch vụ tiện ích và các khoản phát sinh trong lưu trú.',
    'invoices': 'Theo dõi hóa đơn, thanh toán và xuất chứng từ PDF.',
    'reports': 'Xem doanh thu đã ghi nhận theo khoảng ngày.',
    'chat': 'Tư vấn tự động dựa trên dữ liệu khách sạn.',
    'users': 'Tạo và quản lý tài khoản nhân viên.',
    'logs': 'Theo dõi hoạt động nghiệp vụ trong hệ thống.',
}
