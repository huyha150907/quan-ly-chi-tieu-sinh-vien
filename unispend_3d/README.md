# UniSpend

Giao diện UTH Spend có thanh bên với bốn mục Lịch tài chính, Thống kê chi tiêu, Nhập Thu / Chi & CSV và Cảnh báo & Ngân sách. Giao dịch và ngân sách được lưu vào SQLite.

Từ thư mục gốc dự án, chạy:

```powershell
python unispend_3d/main.py
```

Nếu chưa cài thư viện, chạy từ thư mục gốc:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe unispend_3d/main.py
```

Giao diện mở trên trình duyệt. Giữ Terminal mở khi dùng ứng dụng; nhấn **Ctrl+C** để dừng.

Trong mục **Nhập Thu / Chi & CSV**, điền thông tin rồi bấm **Nhập khoản giao dịch**. Sau khi lưu, ứng dụng mở báo cáo của tháng giao dịch.

Để nạp nhiều giao dịch, vào **Nhập Thu / Chi & CSV → Nhập giao dịch từ CSV**. Chọn tệp CSV UTF-8, kiểm tra tối đa 5 giao dịch trong phần xem trước rồi bấm **Xác nhận nhập vào sổ**. Bạn có thể dùng tệp xuất từ ứng dụng hoặc CSV có các cột `Ngày`, `Loại`, `Danh mục`, `Số tiền (VNĐ)` và cột `Ghi chú` tùy chọn. Nếu một dòng sai, ứng dụng báo số dòng để bạn sửa trước khi lưu cả lô.

Lần đầu khởi tạo, UniSpend tạo dữ liệu mẫu bốn tháng trong `unispend_3d/data/student_expense.db`. Dùng `--db` để chọn tệp riêng hoặc mở cơ sở dữ liệu UniSpend có sẵn:

```powershell
python unispend_3d/main.py --db 'D:\du-lieu\student_expense.db'
```

## FastAPI

Mở một terminal khác để chạy API song song với giao diện:

```powershell
python unispend_3d/main.py --api
```

Mở [Swagger UI](http://127.0.0.1:8000/docs) để thử các endpoint. FastAPI và Streamlit dùng chung tệp SQLite. Nếu chọn tệp bằng `--db`, hãy truyền cùng đường dẫn cho cả hai lệnh.

| Endpoint | Chức năng |
| --- | --- |
| `GET /health` | Kiểm tra máy chủ API |
| `GET /api/months` | Liệt kê tháng báo cáo |
| `GET /api/categories?tx_type=Chi tiêu` | Liệt kê danh mục theo loại giao dịch |
| `GET /api/transactions` | Xem giao dịch và lọc theo `month`, `tx_type`, `category`, `q` (ghi chú) |
| `POST /api/transactions` | Tạo giao dịch và trả về mã giao dịch |
| `DELETE /api/transactions/{transaction_id}` | Xóa giao dịch |
| `GET /api/dashboard/{month}` | Xem tổng thu chi, ngân sách và cảnh báo |
| `GET /api/charts/{month}` | Lấy dữ liệu biểu đồ |
| `GET` hoặc `PUT /api/budgets/{month}` | Xem hoặc lưu tổng ngân sách và toàn bộ định mức danh mục |

Tháng sử dụng định dạng `YYYY-MM`. Với `PUT`, có thể lấy JSON từ `GET`, bỏ trường `month`, chỉnh các giá trị cần thiết rồi gửi lại.
