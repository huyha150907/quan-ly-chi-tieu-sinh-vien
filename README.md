# UniSpend — Quản lý chi tiêu sinh viên

Ứng dụng Python giúp sinh viên ghi lại thu nhập, chi tiêu hằng ngày, theo dõi ngân sách và xem biểu đồ theo tháng. Giao diện Streamlit mở trên trình duyệt; dữ liệu được lưu bằng SQLite trên máy của bạn. Biểu đồ dùng Altair và dữ liệu bảng dùng pandas.

## 1. Cài đặt và chạy

Cài Python 3.10 trở lên. Mở PowerShell tại thư mục dự án, tạo môi trường riêng rồi cài các thư viện:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

`python main.py` hoặc `RUN.bat` mở giao diện UTH Spend có Lịch tài chính và mục **Nhập Thu / Chi & CSV** ở thanh bên. Giữ Terminal mở khi sử dụng. Nhấn **Ctrl+C** để dừng.

Với dữ liệu từ giao diện UniSpend đời trước, dùng `python main.py --legacy`. Hai lệnh sau dành cho dữ liệu của giao diện đó:

```powershell
.venv\Scripts\python.exe main.py --demo
.venv\Scripts\python.exe main.py --db data/bai_thuyet_trinh.db
```

Giao diện đời trước dùng `data/expenses.db`, ban đầu chưa có giao dịch. Chế độ mẫu dùng `data/demo.db` riêng, có dữ liệu tháng hiện tại và năm tháng trước. Mở lại chế độ mẫu không chèn trùng dữ liệu; các chỉnh sửa được lưu trong tệp mẫu. Không dùng đồng thời `--demo` và `--db`.

### Giao diện UniSpend và FastAPI

Giao diện UTH Spend có lịch tài chính, sổ thu chi, biểu đồ và ngân sách. Chạy lệnh đầu trong terminal để mở giao diện, và lệnh thứ hai trong terminal riêng để chạy FastAPI:

```powershell
python main.py
python main.py --api
```

Sau khi chạy API, mở [Swagger UI](http://127.0.0.1:8000/docs). Xem hướng dẫn chọn tệp SQLite và danh sách endpoint trong [tài liệu UniSpend](unispend_3d/README.md).

Trên Streamlit Community Cloud, chọn nhánh `main` và tệp chạy `app.py`. Bản triển khai tạo dữ liệu mẫu riêng.

## 2. Hướng dẫn sử dụng giao diện đời trước

**Thanh bên:** chọn tháng báo cáo và nhập nhanh giao dịch. Chọn loại thu/chi, danh mục, ngày, số tiền và ghi chú rồi lưu. Tháng chưa có dữ liệu có tổng thu, tổng chi bằng 0.

Bốn tab chính:

| Tab | Chức năng |
| --- | --- |
| Tổng quan | Tổng thu, tổng chi, chênh lệch, ngân sách; ba khoản thiết yếu Tiền ăn, Tiền trọ, Đi lại; bảng danh mục và biểu đồ cơ cấu |
| Biểu đồ theo tháng | So sánh thu/chi và phân tích chi tiêu theo danh mục, khoản thiết yếu và từng ngày |
| Cảnh báo & Ngân sách | Xem cảnh báo, đặt hoặc điều chỉnh hạn mức tổng và từng danh mục theo tháng |
| Sổ giao dịch | Lọc theo loại, danh mục, ghi chú; sửa giao dịch, xóa có xác nhận và xuất CSV các giao dịch đang lọc |

Chênh lệch là **tổng thu trừ tổng chi trong tháng đang chọn**, không phải số dư tài khoản ngân hàng hay tiền tích lũy qua các tháng. Thẻ Tiền ăn sử dụng dữ liệu thuộc danh mục Ăn uống.

Số tiền tính bằng đồng Việt Nam, phải là số nguyên dương, tối đa `1.000.000.000.000` đồng. Nhập số tiền liền nhau, ví dụ `1200000`. Ngày không tồn tại, số tiền không hợp lệ và ghi chú quá 200 ký tự sẽ bị từ chối.

| Loại giao dịch | Danh mục |
| --- | --- |
| Chi tiêu | Ăn uống, Tiền trọ, Đi lại, Học tập, Giải trí, Khác |
| Thu nhập | Gia đình hỗ trợ, Làm thêm, Học bổng, Khác |

### Quy tắc ngân sách

Đặt hạn mức cho **Tổng chi tiêu** hoặc một danh mục của tháng đang chọn. Ngân sách được lưu riêng cho từng tháng và không tự chuyển sang tháng sau.

- Dưới 80%: trong ngân sách.
- Từ 80% đến 100%: cảnh báo sắp hết ngân sách.
- Trên 100%: cảnh báo vượt ngân sách.

Tiền thu không làm giảm tổng chi dùng để so sánh với hạn mức. Khi chưa đặt ngân sách, ứng dụng vẫn thống kê nhưng chưa thể đánh giá mức chi của mục đó. Cảnh báo chỉ hiển thị trong ứng dụng.

### Xuất và sao lưu

CSV được xuất theo bộ lọc hiện tại, dùng UTF-8 có BOM để hỗ trợ tiếng Việt trong Excel. Để sao lưu toàn bộ dữ liệu, dừng ứng dụng rồi sao chép tệp `.db` đang sử dụng. Mở bản sao bằng tùy chọn `--db`.

## 3. Phân tích bài toán

**Đề tài:** Xây dựng ứng dụng quản lý chi tiêu sinh viên bằng Python.

Sinh viên thường có nguồn thu giới hạn và nhiều khoản chi nhỏ. Việc ghi chép và tổng hợp giúp nhận biết tiền đã được dùng vào đâu, đồng thời phát hiện sớm khi gần hết ngân sách. Đề tài vận dụng xử lý dữ liệu, lập trình hướng đối tượng, cơ sở dữ liệu và giao diện Python.

**Đối tượng sử dụng:** sinh viên tự quản lý chi tiêu cá nhân trên một máy tính.

| Dữ liệu đầu vào | Kết quả đầu ra |
| --- | --- |
| Ngày, loại, danh mục, số tiền, ghi chú | Giao dịch có thể tìm kiếm, sửa và xóa |
| Tháng báo cáo và điều kiện lọc | Tổng thu, tổng chi, chênh lệch, thống kê và biểu đồ |
| Hạn mức tổng hoặc danh mục | Số đã dùng, còn lại và trạng thái cảnh báo |
| Lệnh xuất dữ liệu | Tệp CSV để đối chiếu hoặc xử lý tiếp |

## 4. Thiết kế chương trình

### Luồng xử lý

```text
Khởi động main.py -> mở giao diện Streamlit từ app.py
    -> Mở hoặc tạo SQLite, nạp dữ liệu tháng được chọn
    -> Người dùng nhập hoặc thay đổi dữ liệu
    -> Kiểm tra ngày, loại, danh mục, số tiền và ghi chú
       -> Không hợp lệ: hiển thị lỗi để sửa
       -> Hợp lệ: lưu SQLite
    -> Cập nhật tổng thu chi, cảnh báo, bảng và biểu đồ
```

### Cấu trúc thư mục

```text
pycuoiky/
├── main.py                  # Khởi động Streamlit, nhận --demo và --db
├── app.py                   # Điểm vào của ứng dụng Streamlit
├── RUN.bat                  # Chạy chế độ thông thường
├── DEMO.bat                 # Chạy chế độ dữ liệu mẫu
├── requirements.txt         # Streamlit, pandas, Altair
├── README.md
├── expense_tracker/
│   ├── __init__.py
│   ├── storage.py           # Mô hình dữ liệu, SQLite và tính toán
│   ├── ui.py                # Dựng giao diện Streamlit và xử lý thao tác
│   ├── charts.py            # Tạo biểu đồ Altair
│   └── utils.py             # Định dạng tiền, ngày và chuyển đổi dữ liệu
├── tests/
│   ├── test_storage.py      # Nghiệp vụ và lưu trữ
│   └── test_utils.py        # Tiền tệ và chuyển tháng
└── data/                    # Tự tạo khi chạy
    ├── expenses.db          # Dữ liệu cá nhân
    └── demo.db              # Dữ liệu trình diễn
```

| Thành phần | Vai trò |
| --- | --- |
| `Transaction` | Một giao dịch gồm mã, ngày, loại, danh mục, số tiền và ghi chú |
| `BudgetStatus` | Hạn mức, số đã chi, còn lại và trạng thái cảnh báo |
| `ExpenseStore` | Quản lý SQLite; thêm, sửa, xóa, lọc, tổng hợp và xuất dữ liệu |
| `ui.py` | Nhận thao tác, gọi lớp lưu trữ, trình bày kết quả bằng Streamlit |
| `charts.py` | Chuyển dữ liệu tổng hợp thành biểu đồ Altair |
| `utils.py` | Quy tắc hiển thị và chuyển đổi dữ liệu dùng chung |

Phần giao diện tách khỏi lưu trữ để dễ chia việc và kiểm thử nghiệp vụ. SQLite lưu tiền bằng số nguyên đồng Việt Nam để tránh sai số số thực; truy vấn nhận dữ liệu nhập đều dùng tham số SQL.

```text
Tổng thu tháng = tổng các giao dịch thu trong tháng
Tổng chi tháng = tổng các giao dịch chi trong tháng
Chênh lệch tháng = tổng thu tháng - tổng chi tháng
Chi theo danh mục = tổng các giao dịch chi thuộc danh mục trong tháng
Ngân sách còn lại = hạn mức - số đã chi
Tỷ lệ sử dụng = số đã chi / hạn mức × 100%
```

## 5. Kiểm thử và trình diễn

Chạy kiểm thử nghiệp vụ từ thư mục dự án:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kiểm thử dùng dữ liệu tạm, tập trung vào lưu/đọc dữ liệu, thêm/sửa/xóa, đầu vào không hợp lệ, bộ lọc, tổng hợp tháng, cảnh báo ngân sách và xuất CSV. Ghi lại kết quả chạy thực tế của phiên bản hiện tại trước khi nộp bài.

| Kịch bản thủ công | Kết quả cần kiểm tra |
| --- | --- |
| Mở tệp dữ liệu mới | Các tổng bằng 0, có hướng dẫn khi chưa có dữ liệu |
| Thêm thu 5.000.000 và chi ăn uống 50.000 cùng tháng | Chênh lệch 4.950.000 đồng, bảng và biểu đồ cập nhật |
| Sửa khoản chi thành 60.000 | Tổng chi và thống kê Ăn uống cùng thay đổi |
| Xóa sau khi xác nhận | Bản ghi biến mất, tổng giảm tương ứng |
| Nhập ngày sai, số tiền âm hoặc ghi chú quá dài | Hiển thị lỗi và không lưu |
| Lọc giao dịch rồi xuất CSV | CSV chỉ chứa các dòng khớp bộ lọc; tiếng Việt hiển thị đúng |
| Chuyển giữa tháng 12 và tháng 1 năm sau | Dữ liệu được phân đúng tháng, năm |
| Dừng rồi mở lại cùng tệp | Giao dịch và ngân sách vẫn còn |

Để minh họa cảnh báo, dùng tệp thử riêng: đặt tổng ngân sách 3.000.000 đồng, nhập tổng chi 2.400.000 đồng để đạt 80%, rồi tăng lên 3.100.000 đồng để vượt 100.000 đồng. Sửa hoặc xóa giao dịch và kiểm tra trạng thái cập nhật.

Khi trình bày, chạy `python main.py --demo`, giới thiệu thanh bên và bốn tab, thêm giao dịch, minh họa cảnh báo, xem biểu đồ và xuất CSV. Bổ sung ảnh giao diện và kết quả kiểm thử thực tế vào báo cáo.

## 6. Đánh giá và hướng phát triển

**Ưu điểm:** giao diện trình duyệt, dữ liệu lưu cục bộ, kiểm tra đầu vào, cảnh báo ngân sách, biểu đồ tương tác và xuất CSV. Cấu trúc module giúp giải thích vai trò của Python trong từng bước xử lý.

**Hạn chế:** dành cho một người dùng trên một máy; chưa đồng bộ điện thoại, đăng nhập, mã hóa cơ sở dữ liệu, nhập sao kê hoặc chia sẻ chi tiêu nhóm. Danh mục được định sẵn; ngân sách cần đặt cho từng tháng.

**Hướng phát triển:** danh mục tùy chỉnh, sao lưu/khôi phục qua giao diện, giao dịch định kỳ, nhập CSV có kiểm tra và so sánh nhiều kỳ.

Trước khi nộp bài, bổ sung tên thành viên, phân công và các minh chứng theo yêu cầu của giảng viên. Mỗi thành viên nên hiểu luồng xử lý, cách tính ngân sách và phần mã mình phụ trách.
