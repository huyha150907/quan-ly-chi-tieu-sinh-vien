# UniSpend 3D

Bản giao diện UniSpend 3D có thẻ ví lật, hiệu ứng nghiêng theo chuột, thống kê thu chi và cảnh báo ngân sách. Mã nguồn được đóng gói từ bản đang chạy trong thư mục `quan_ly_chi_tieu_sv`.

Từ thư mục gốc dự án, chạy:

```powershell
python unispend_3d/main.py
```

Launcher dùng Python hiện tại; nếu thiếu Streamlit, chương trình tự tìm Python trong `.venv` ở thư mục gốc. Nếu chưa cài thư viện:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe unispend_3d/main.py
```

Giao diện mở trên trình duyệt. Giữ Terminal mở khi dùng ứng dụng; nhấn **Ctrl+C** để dừng.

Dữ liệu được tự khởi tạo với mẫu bốn tháng gần nhất trong `unispend_3d/data/student_expense.db`. Đây là tệp dữ liệu riêng; không dùng hoặc chuyển cơ sở dữ liệu của giao diện ở thư mục gốc. Gói mã nguồn không kèm dữ liệu hay cache từ máy đang chạy.
