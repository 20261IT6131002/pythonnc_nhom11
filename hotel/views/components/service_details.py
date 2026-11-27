"""Read-only service ledger shared by staff and customer screens."""
import tkinter as tk
from tkinter import ttk

from hotel.views.components.widget_helpers import add_tree, error, pretty


def show_booking_services(parent, controller, booking_id):
    details = controller.booking_service_details(booking_id)
    dialog = tk.Toplevel(parent)
    dialog.title(f"Dịch vụ và chi phí — {details['code']}")
    dialog.geometry('1080x650')
    dialog.minsize(760, 480)
    dialog.transient(parent.winfo_toplevel())
    panel = ttk.Frame(dialog, padding=18)
    panel.pack(fill='both', expand=True)
    content = ttk.Frame(panel)
    content.pack(fill='both', expand=True)

    def render(data):
        for child in content.winfo_children():
            child.destroy()
        ttk.Label(content, text=f"{data['code']} · Phòng {data['room']} · {data['customer']}",
                  style='FormTitle.TLabel', wraplength=1000).pack(anchor='w')
        state = f"Hóa đơn #{data['invoice_id']}" if data['invoice_id'] else 'Bảng kê tạm tính'
        ttk.Label(content, text=f"{pretty(data['status'])} · {state}").pack(anchor='w', pady=(6, 10))
        summary = ttk.Frame(content)
        summary.pack(fill='x')
        totals = [('Tiền phòng', data['room_total']), ('Dịch vụ đã ghi phí', data['service_total']),
                  ('Giảm giá', data['discount']),
                  ('Tổng đã chốt' if data['invoice_id'] else 'Tổng tạm tính', data['total']),
                  ('Đã thanh toán', data['paid']),
                  ('Còn phải trả' if data['invoice_id'] else 'Còn lại tạm tính', data['due'])]
        for index, (label, value) in enumerate(totals):
            ttk.Label(summary, text=f'{label}\n{value}', padding=(0, 5)).grid(
                row=index // 3, column=index % 3, sticky='w', padx=(0, 18))
        for column in range(3):
            summary.columnconfigure(column, weight=1)
        ttk.Label(content, text=f"Dịch vụ chờ xác nhận / đã xác nhận: {data['open_total']}. "
                  'Các yêu cầu này được ghi phí khi hoàn thành.', wraplength=1000).pack(
                      anchor='w', pady=(8, 2))
        add_tree(content, [('source', 'Nguồn', 145), ('service', 'Dịch vụ', 160),
            ('quantity', 'SL', 45), ('unit_price', 'Đơn giá', 120), ('amount', 'Thành tiền', 130),
            ('status', 'Trạng thái', 130), ('created_at', 'Ngày tạo (giờ VN)', 150),
            ('scheduled_at', 'Lịch hẹn (giờ VN)', 160), ('notes', 'Ghi chú', 200)], data['rows'], height=7)

    def refresh():
        try:
            render(controller.booking_service_details(booking_id))
        except Exception as exc:
            error(dialog, exc)

    bar = ttk.Frame(panel)
    bar.pack(fill='x', pady=(12, 0))
    ttk.Button(bar, text='Làm mới', command=refresh).pack(side='left')
    ttk.Button(bar, text='Đóng', command=dialog.destroy).pack(side='right')
    render(details)
    return dialog
