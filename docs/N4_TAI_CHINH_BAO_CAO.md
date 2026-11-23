# GrandStay — Phân hệ N4: Tài chính & Báo cáo

Phân hệ **N4** chịu trách nhiệm toàn diện về quản lý dòng tiền, hóa đơn, thanh toán, đặt cọc, hoàn tiền, thống kê doanh thu và tự động hóa email chứng từ của khách sạn GrandStay theo đúng mô hình kiến trúc **MVC (Model - View - Controller)**.

---

## 1. Kiến trúc phân lớp MVC của N4

```text
┌────────────────────────────────────────────────────────────────────────┐
│                                 VIEW                                   │
│  • hotel/views/screens/billing.py (BillingScreenMixin: thu tiền, cọc,  │
│    hoàn tiền, chi tiết hóa đơn, xuất PDF, gửi email)                   │
│  • hotel/views/screens/bookings.py (BookingsScreenMixin: thu cọc, hoàn)│
│  • hotel/views/admin/dashboard.py (AdminReportsMixin: KPI, cơ cấu, PDF)│
│  • hotel/views/customer/lookup.py (Khách xem cọc, tình trạng, tải PDF) │
│  • hotel/views/pages.py (Tabs: invoices, deposits, refunds, reports)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                              CONTROLLER                                │
│  • hotel/controllers/billing_controller.py (BillingControllerMixin)    │
│    - make_invoice, pay, record_deposit, record_refund                  │
│    - export_invoice, export_deposit_receipt, export_refund_receipt      │
│    - send_invoice_email, send_deposit_email, send_refund_email         │
│    - get_invoice_details, comprehensive_report, export_report           │
│  • hotel/controllers/catalog_controller.py (dữ liệu bảng deposits/...) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                         SERVICE & REPOSITORY                           │
│  • hotel/services/finance.py:                                          │
│    - record_deposit, suggest_cancellation_refund, record_refund        │
│    - comprehensive_financial_report (Gross, Net, cơ cấu, công nợ)     │
│  • hotel/services/finance_mailer.py:                                   │
│    - send_deposit_confirmation, send_invoice_notification             │
│    - send_refund_notification, send_payment_receipt                    │
│  • hotel/services/pdf_service.py:                                      │
│    - invoice_pdf, deposit_receipt_pdf, refund_receipt_pdf              │
│    - comprehensive_report_pdf, report_pdf                              │
│  • hotel/services/mailer.py:                                           │
│    - send_email_with_attachment (MIME PDF attachment via SMTP)         │
│  • hotel/services/business.py:                                         │
│    - ensure_invoice, invoice_due (tự động cấn trừ tiền cọc)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                                 MODEL                                  │
│  • hotel/models/billing.py:                                            │
│    - Invoice (invoices): room, services, discount, total, timestamps   │
│    - Payment (payments): amount, method, reference, recorded_by        │
│    - BookingDeposit (booking_deposits): amount, method, status, notes  │
│    - Refund (refunds): amount, method, reason, status, recorded_by     │
│  • hotel/models/bookings.py: Booking (quan hệ deposits, refunds)       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Chi tiết 6 khối chức năng cốt lõi

### 2.1. Đặt cọc (Deposits)
- **Mục đích:** Giữ chỗ cho khách đặt phòng trước, tránh tình trạng đặt ảo / bỏ phòng (no-show).
- **Quy tắc:**
  - Hỗ trợ các hình thức: Tiền mặt (`cash`), Chuyển khoản (`bank_transfer`), Thẻ (`card_manual`).
  - Kiểm tra số tiền cọc: `> 0` và không vượt quá 150% tiền phòng dự kiến.
  - Gợi ý mức cọc tiêu chuẩn: 30% tiền phòng hoặc tối thiểu 1 đêm.
  - **Tự động chuyển trạng thái:** Nếu đơn đang ở trạng thái `pending` (chờ xác nhận), khi nhận cọc thành công hệ thống tự động đổi sang `confirmed`.
  - **Email & PDF:** Tự động gửi email xác nhận đặt cọc kèm **Phiếu thu tiền đặt cọc PDF** có mã tham chiếu giao dịch.

### 2.2. Hóa đơn (Invoices)
- **Mục đích:** Chốt chi phí lưu trú khi khách làm thủ tục thanh toán / trả phòng.
- **Quy tắc & Cấn trừ cọc:**
  - Hóa đơn bao gồm: Tiền phòng (theo số đêm thực tế) + Tiền dịch vụ phát sinh - Giảm giá khuyến mãi (nếu có).
  - **Tự động cấn trừ tiền cọc:** Số tiền cọc đã nộp được trừ trực tiếp vào số tiền cần thanh toán (`invoice_due = total - deposits - payments + refunds`).
  - Hóa đơn hiển thị rõ ràng từng dòng: Tiền phòng, Chi tiết dịch vụ, Mức giảm giá, Tiền cọc đã cấn trừ, Đã thanh toán thêm, Còn thiếu, và Trạng thái (`Đã thanh toán đủ` hoặc `Còn thiếu X VND`).
  - Cho phép xuất hóa đơn ra file PDF chất lượng cao hoặc xem hộp thoại chi tiết tài chính.

### 2.3. Thanh toán (Payments)
- **Mục đích:** Thu tiền thanh toán hóa đơn.
- **Quy tắc:**
  - Hỗ trợ thanh toán nhiều đợt (thanh toán từng phần).
  - Kiểm tra nghiêm ngặt: Số tiền thu `> 0` và **không được vượt quá số tiền còn thiếu** của hóa đơn (`invoice_due`).
  - Chống thu vượt (MySQL row locking `with_for_update` trên bản ghi hóa đơn).
  - Khách chỉ được phép hoàn tất trả phòng (`checked_out`) khi số tiền còn thiếu của hóa đơn bằng 0.
  - Tự động gửi email biên lai thanh toán cho khách hàng.

### 2.4. Hoàn tiền (Refunds)
- **Mục đích:** Xử lý trả lại tiền cho khách khi hủy phòng, hoàn tiền cọc hoặc điều chỉnh hóa đơn thừa tiền.
- **Chính sách hoàn hủy tự động (Cancellation Policy Engine):**
  - Hủy trước ngày nhận phòng **≥ 3 ngày:** Gợi ý hoàn **100%** số tiền đã đóng.
  - Hủy trước ngày nhận phòng **1 đến 2 ngày:** Gợi ý hoàn **50%** (thu phí phạt hủy 50%).
  - Hủy trong ngày nhận phòng hoặc sau đó: Gợi ý hoàn **0%** (thu phí phạt hủy 100%).
  - Nhân viên có quyền điều chỉnh số tiền hoàn theo thỏa thuận thực tế (nhưng không được vượt quá số tiền đã thu trừ số tiền đã hoàn trước đó).
- **Chứng từ:** Xuất **Phiếu chi hoàn tiền PDF** và gửi email thông báo hoàn tiền chính thức cho khách hàng.

### 2.5. Thống kê & Báo cáo doanh thu (Statistics & Reports)
- **Dành riêng cho Quản trị viên (Admin):**
  - **Thẻ chỉ số tổng quan (KPIs):**
    - Doanh thu thanh toán hóa đơn (`Payments Total`).
    - Tiền đặt cọc nhận vào (`Deposits Total`).
    - Tiền đã hoàn trả lại cho khách (`Refunds Total`).
    - **DOANH THU THUẦN (Net Revenue)** = `(Thanh toán + Cọc) - Hoàn tiền`.
    - Công nợ còn phải thu (`Outstanding Due`).
  - **Cơ cấu theo Loại phòng:** Thống kê số lượt thuê, doanh thu tiền phòng, dịch vụ và tổng tiền theo từng loại phòng (Deluxe, Standard, Suite...).
  - **Cơ cấu theo Phương thức thanh toán:** Thu thanh toán, thu đặt cọc, chi hoàn tiền và thực thu thuần theo Tiền mặt, Chuyển khoản, Thẻ.
  - **Nhật ký giao dịch chi tiết:** Toàn bộ các khoản thu chi trong khoảng ngày lọc với mã GD, mã đơn, khách hàng, số tiền, hình thức và ghi chú.
  - **Xuất PDF:** Hỗ trợ xuất **Báo cáo tài chính toàn diện PDF** và Báo cáo danh sách giao dịch.

### 2.6. Email tài chính tự động (Finance Mailer)
- Hỗ trợ gửi email HTML / Plain text kèm **file đính kèm MIME PDF** (hóa đơn, phiếu thu, phiếu chi).
- Tự động nhận diện email khách hàng từ hồ sơ đặt phòng hoặc tài khoản thành viên.
- Bao gồm các luồng:
  - Gửi xác nhận đặt cọc + file PDF phiếu cọc.
  - Gửi hóa đơn thanh toán + file PDF hóa đơn.
  - Gửi thông báo hoàn tiền + file PDF phiếu chi hoàn tiền.
  - Gửi biên nhận thanh toán từng lần.

---

## 3. Danh sách màn hình & Thao tác trên giao diện Tkinter

### 3.1. Tab "Hóa đơn" (`invoices`)
- Cột bảng: `ID`, `Mã đặt`, `Khách`, `Tiền phòng`, `Dịch vụ`, `Giảm giá`, `Đã cọc`, `Tổng cộng`, `Đã thu`, `Còn thiếu`, `Trạng thái`.
- Nút chức năng:
  - **Ghi nhận thanh toán:** Nhập số tiền thu, hình thức, mã tham chiếu.
  - **Xuất hóa đơn PDF:** Lưu tệp PDF về máy tính.
  - **Gửi hóa đơn Email:** Gửi trực tiếp tệp PDF hóa đơn qua Gmail của khách.
  - **Chi tiết hóa đơn:** Xem phân rã từng khoản thu chi và lịch sử thanh toán/cọc/hoàn.
  - **Hoàn tiền:** Hoàn tiền trực tiếp từ hóa đơn.

### 3.2. Tab "Đặt cọc" (`deposits`)
- Cột bảng: `ID`, `Mã đặt phòng`, `Khách hàng`, `Phòng`, `Số tiền cọc`, `Hình thức`, `Trạng thái`, `Tham chiếu / Ghi chú`, `Ngày thu`.
- Nút chức năng:
  - **Thu tiền cọc:** Chọn đơn đặt phòng và ghi nhận tiền cọc.
  - **Xuất phiếu cọc PDF:** Xuất phiếu thu tiền đặt cọc.
  - **Gửi email phiếu cọc:** Gửi email phiếu cọc cho khách.
  - **Hoàn cọc:** Thực hiện hoàn trả tiền cọc cho khách.

### 3.3. Tab "Hoàn tiền" (`refunds`)
- Cột bảng: `ID`, `Mã đặt phòng`, `Khách hàng`, `Số tiền hoàn`, `Hình thức`, `Lý do hoàn tiền`, `Trạng thái`, `Ngày hoàn`.
- Nút chức năng:
  - **Ghi nhận hoàn tiền:** Chọn đơn, hệ thống hiển thị chính sách gợi ý và xử lý hoàn.
  - **Xuất phiếu hoàn PDF:** Xuất phiếu chi hoàn tiền.
  - **Gửi email hoàn tiền:** Gửi email xác nhận hoàn tiền cho khách.

### 3.4. Tab "Đặt phòng" (`bookings`)
- Bổ sung nút:
  - **Ghi nhận đặt cọc:** Thu cọc nhanh cho đơn vừa tạo.
  - **Hoàn tiền:** Xử lý hoàn tiền ngay khi hủy đơn.

### 3.5. Tab "Thống kê doanh thu" (`reports` - Admin)
- Bộ lọc từ ngày → đến ngày.
- 5 thẻ chỉ số tài chính (Doanh thu hóa đơn, Tiền cọc, Hoàn tiền, Doanh thu thuần, Công nợ).
- 3 tab con hiển thị trực quan:
  1. *Tất cả giao dịch:* Chi tiết từng dòng thanh toán, cọc, hoàn.
  2. *Cơ cấu Loại phòng:* Doanh số phòng & dịch vụ theo từng hạng phòng.
  3. *Phương thức thanh toán:* Bảng cân đối thu chi theo Tiền mặt, Chuyển khoản, Thẻ.
- Nút **Xuất PDF Báo cáo toàn diện** & **Xuất PDF Giao dịch**.

### 3.6. Phía Khách hàng (Tra cứu & Hồ sơ)
- Tại màn hình **Tra cứu đặt phòng**: Hiển thị rõ số tiền cọc đã nộp, tổng hóa đơn, số tiền còn thiếu và nút **Tải hóa đơn PDF ↗**.

---

## 4. Hướng dẫn kiểm thử

Bộ kiểm thử N4 được đặt tại file `tests/test_n4_finance.py`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_n4_finance.py -v
```

Kiểm thử toàn bộ hệ thống (8 test suite):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
