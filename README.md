# Ứng dụng quản lý chi tiêu sinh viên

Ứng dụng Python giúp sinh viên ghi lại thu nhập và chi tiêu hằng ngày, theo dõi ngân sách và xem biểu đồ theo tháng. Chương trình chạy trên máy tính, lưu dữ liệu bằng SQLite và dùng Tkinter để tạo giao diện. Không cần tài khoản, kết nối Internet hay cài thư viện Python bên ngoài để sử dụng.

## 1. Chạy chương trình

Cài Python 3.10 trở lên có Tkinter. Trên Windows, bản cài đặt Python thông thường đã có Tkinter và SQLite.

Mở thư mục dự án rồi nhấp đúp **RUN.bat**, hoặc mở Terminal tại thư mục này và chạy:

```powershell
python main.py
```

Để xem ứng dụng với dữ liệu mẫu, nhấp đúp **DEMO.bat** hoặc chạy:

```powershell
python main.py --demo
```

Chế độ thường dùng `data/expenses.db`, ban đầu chưa có giao dịch. Chế độ mẫu dùng `data/demo.db` riêng, có dữ liệu của tháng hiện tại và năm tháng trước. Mở lại chế độ mẫu không chèn trùng dữ liệu. Việc chỉnh sửa dữ liệu mẫu cũng được lưu lại trong tệp mẫu.

Có thể chọn tệp dữ liệu khác:

```powershell
python main.py --db data/bai_thuyet_trinh.db
```

Nếu máy dùng lệnh `py` thay cho `python`, thay tên lệnh tương ứng. Nếu gặp lỗi thiếu Tkinter, chạy lại trình cài đặt Python và bật thành phần **Tcl/Tk and IDLE**. Có thể kiểm tra Tkinter bằng lệnh `python -m tkinter`.

## 2. Hướng dẫn sử dụng

### Tổng quan

Chọn tháng cần xem để theo dõi tổng thu, tổng chi, chênh lệch thu chi và các giao dịch gần đây. Chênh lệch được tính trong tháng đang chọn, không phải số dư tài khoản ngân hàng hay tiền tích lũy qua các tháng.

Biểu đồ giúp nhận biết danh mục tốn nhiều tiền và so sánh thu chi giữa các tháng. Tháng chưa có dữ liệu có tổng thu, tổng chi bằng 0.

### Giao dịch

1. Chọn thêm giao dịch hoặc nhấn **Ctrl+N**.
2. Chọn thu nhập hoặc chi tiêu, nhập ngày theo dạng `YYYY-MM-DD`, danh mục, số tiền và ghi chú nếu có.
3. Lưu giao dịch. Dùng chức năng sửa khi cần điều chỉnh và xóa khi muốn bỏ một bản ghi.
4. Lọc theo tháng, loại giao dịch, danh mục hoặc từ khóa để tìm lại khoản đã nhập.
5. Xuất CSV để xem hoặc xử lý tiếp bằng Excel. Tệp dùng UTF-8 có BOM để hỗ trợ tiếng Việt.

Số tiền tính bằng đồng Việt Nam, phải là số nguyên dương và không vượt quá `1.000.000.000.000` đồng. Có thể nhập `1200000` hoặc dạng có phân cách hàng nghìn như `1.200.000`. Ngày không tồn tại, số tiền không hợp lệ và ghi chú quá 200 ký tự sẽ bị từ chối.

| Loại giao dịch | Danh mục |
| --- | --- |
| Chi tiêu | Ăn uống, Tiền trọ, Đi lại, Học tập, Giải trí, Khác |
| Thu nhập | Gia đình hỗ trợ, Làm thêm, Học bổng, Khác |

### Ngân sách

Đặt hạn mức cho **Tổng chi tiêu** hoặc một danh mục chi tiêu của tháng đang chọn. Ngân sách mỗi tháng được lưu riêng; đặt ngân sách tháng này không tự tạo ngân sách cho tháng sau.

- Dưới 80%: tiếp tục theo dõi mức chi.
- Từ 80% đến 100%: cảnh báo sắp hết ngân sách.
- Trên 100%: cảnh báo đã vượt ngân sách.

Tiền thu không làm giảm tổng chi dùng để so sánh với ngân sách. Khi chưa đặt hạn mức, chương trình vẫn thống kê chi tiêu nhưng chưa có cơ sở để cảnh báo cho danh mục đó. Cảnh báo hiển thị trong ứng dụng; chương trình không gửi email hay thông báo khi đã đóng.

### Thống kê

Xem tổng chi theo danh mục trong tháng được chọn và biểu đồ thu chi của sáu tháng kết thúc ở tháng đó. Các biểu đồ được vẽ trực tiếp bằng `tkinter.Canvas`.

### Sao lưu dữ liệu

Đóng ứng dụng rồi sao chép tệp `.db` đang sử dụng sang nơi lưu trữ khác. Để mở bản sao lưu, dùng tùy chọn `--db` và đường dẫn đến bản sao. Giữ riêng tệp dữ liệu cá nhân và tệp dữ liệu dùng để trình diễn.

## 3. Phân tích bài toán

**Tên đề tài:** Xây dựng ứng dụng quản lý chi tiêu sinh viên bằng Python.

**Lý do chọn đề tài:** Sinh viên thường có nguồn thu giới hạn và nhiều khoản chi nhỏ. Nếu không ghi lại thường xuyên, người dùng khó biết tiền đã được dùng vào đâu hoặc nhận ra mình đang vượt khả năng chi trả. Đề tài có phạm vi vừa sức và vận dụng được xử lý dữ liệu, lập trình hướng đối tượng, cơ sở dữ liệu và giao diện Python.

**Bài toán cần giải quyết:** Ghi nhận thu chi theo ngày; tổng hợp chính xác theo tháng và danh mục; so sánh chi tiêu với hạn mức; trình bày kết quả dễ theo dõi.

**Đối tượng sử dụng:** Sinh viên muốn tự quản lý chi tiêu cá nhân trên một máy tính.

| Dữ liệu đầu vào | Kết quả đầu ra |
| --- | --- |
| Ngày, loại giao dịch, danh mục, số tiền, ghi chú | Danh sách giao dịch có thể tìm kiếm, sửa và xóa |
| Tháng cần xem và điều kiện lọc | Tổng thu, tổng chi, chênh lệch và thống kê danh mục |
| Hạn mức tháng cho tổng chi hoặc danh mục | Số tiền đã dùng, còn lại và trạng thái cảnh báo |
| Lệnh xuất dữ liệu | Tệp CSV dùng để đối chiếu hoặc xử lý tiếp |

## 4. Thiết kế chương trình

### Luồng xử lý

```text
Khởi động
    -> Mở hoặc tạo cơ sở dữ liệu SQLite
    -> Hiển thị giao diện và dữ liệu tháng được chọn
    -> Người dùng nhập hoặc thay đổi dữ liệu
    -> Kiểm tra ngày, loại, danh mục và số tiền
       -> Không hợp lệ: thông báo để người dùng sửa
       -> Hợp lệ: lưu SQLite
    -> Tính lại tổng thu chi, ngân sách và biểu đồ
    -> Tiếp tục sử dụng hoặc đóng chương trình
```

### Cấu trúc thư mục

```text
pycuoiky/
├── main.py                  # Điểm khởi động và tham số dòng lệnh
├── RUN.bat                  # Mở chế độ sử dụng thông thường
├── DEMO.bat                 # Mở chế độ dữ liệu mẫu
├── requirements.txt         # Không có phụ thuộc bên ngoài
├── README.md
├── expense_tracker/
│   ├── __init__.py
│   ├── storage.py           # Mô hình dữ liệu, SQLite và tính toán
│   ├── ui.py                # Cửa sổ, biểu mẫu và xử lý thao tác
│   ├── charts.py            # Vẽ biểu đồ bằng Canvas
│   └── utils.py             # Định dạng và chuyển đổi dữ liệu
├── tests/
│   ├── test_storage.py      # Kiểm thử nghiệp vụ và lưu trữ
│   └── test_utils.py        # Kiểm thử tiền tệ và chuyển tháng
└── data/                    # Tự tạo khi chạy chương trình
    ├── expenses.db          # Dữ liệu sử dụng thông thường
    └── demo.db              # Dữ liệu trình diễn
```

### Các thành phần chính

| Thành phần | Vai trò |
| --- | --- |
| `Transaction` | Biểu diễn một giao dịch gồm mã, ngày, loại, danh mục, số tiền và ghi chú |
| `BudgetStatus` | Biểu diễn hạn mức, số tiền đã dùng, số còn lại và trạng thái cảnh báo |
| `ExpenseStore` | Quản lý kết nối SQLite; thêm, sửa, xóa, lọc, tổng hợp và xuất dữ liệu |
| `ui.py` | Nhận thao tác người dùng, gọi lớp lưu trữ và cập nhật giao diện |
| `charts.py` | Chuyển kết quả tổng hợp thành biểu đồ |
| `utils.py` | Dùng chung quy tắc hiển thị tiền và chuyển đổi dữ liệu nhập |

Tách phần giao diện khỏi phần lưu trữ giúp dễ đọc mã, chia việc trong nhóm và kiểm thử các phép tính mà không cần mở cửa sổ.

### Lưu trữ và công thức

SQLite lưu giao dịch và ngân sách trong tệp trên máy. Mỗi giao dịch có mã riêng. Ngân sách gắn với một tháng và một danh mục. Số tiền được lưu bằng số nguyên để tránh sai số số thực khi tính tiền. Câu lệnh SQL dùng tham số để xử lý dữ liệu nhập.

```text
Tổng thu tháng = tổng số tiền của các giao dịch thu trong tháng
Tổng chi tháng = tổng số tiền của các giao dịch chi trong tháng
Chênh lệch tháng = tổng thu tháng - tổng chi tháng
Chi theo danh mục = tổng giao dịch chi thuộc danh mục trong tháng
Ngân sách còn lại = hạn mức - số đã chi
Tỷ lệ sử dụng = số đã chi / hạn mức × 100%
```

Các thư viện dùng trong ứng dụng đều thuộc thư viện chuẩn Python: `tkinter`, `sqlite3`, `datetime`, `csv`, `pathlib`, `argparse`, `dataclasses`, `re` và các tiện ích liên quan. Kiểm thử dùng `unittest` và cơ sở dữ liệu tạm.

## 5. Kiểm thử và chạy trình diễn

Chạy kiểm thử từ thư mục dự án:

```powershell
python -m unittest discover -s tests -v
```

Các phép kiểm thử nghiệp vụ cần bao phủ việc lưu và đọc lại dữ liệu, thêm/sửa/xóa, kiểm tra đầu vào, lọc giao dịch, tổng hợp tháng qua thời điểm chuyển năm, cảnh báo ngân sách và xuất CSV. Dữ liệu kiểm thử dùng tệp tạm để không ảnh hưởng dữ liệu cá nhân.

Kết quả kiểm tra khi hoàn thiện phiên bản này: **27/27 kiểm thử tự động đạt** trên Python 3.14 và Windows. Giao diện đã được chạy thử với dữ liệu trống, dữ liệu mẫu và các tháng ở biên năm 1/9999. Trang Tổng quan và Thống kê có thanh cuộn để xem đầy đủ trên màn hình nhỏ.

### Kịch bản kiểm tra thủ công

| Thao tác | Kết quả cần kiểm tra |
| --- | --- |
| Mở chế độ thường với tệp dữ liệu mới | Danh sách trống, các tổng bằng 0, không phát sinh lỗi |
| Thêm thu nhập 5.000.000 đồng và chi ăn uống 50.000 đồng cùng tháng | Tổng thu 5.000.000, tổng chi 50.000, chênh lệch 4.950.000 đồng |
| Sửa khoản chi thành 60.000 đồng | Tổng chi và thống kê Ăn uống cùng đổi thành 60.000 đồng |
| Xóa khoản chi sau khi xác nhận | Giao dịch biến mất và tổng chi giảm tương ứng |
| Nhập ngày `2026-02-30`, số tiền âm hoặc chữ vào số tiền | Hiển thị lỗi và không lưu giao dịch |
| Chuyển giữa tháng 12 và tháng 1 năm sau | Dữ liệu được phân đúng tháng, năm |
| Đóng rồi mở lại cùng tệp dữ liệu | Các giao dịch và ngân sách đã lưu vẫn còn |
| Xuất CSV rồi mở bằng Excel | Cột dữ liệu và tiếng Việt hiển thị đúng |

Ví dụ dưới đây là kịch bản tự nhập trên tệp thử riêng, không phải mô tả số liệu có sẵn trong chế độ mẫu:

1. Đặt ngân sách **Tổng chi tiêu** của một tháng là 3.000.000 đồng.
2. Nhập các khoản chi với tổng 2.400.000 đồng để kiểm tra mốc cảnh báo 80%.
3. Tăng tổng chi lên 2.900.000 đồng để thấy số tiền còn lại là 100.000 đồng.
4. Thêm khoản chi 200.000 đồng. Tổng chi thành 3.100.000 đồng, vượt 100.000 đồng và xuất hiện cảnh báo vượt ngân sách.
5. Sửa hoặc xóa khoản vừa nhập rồi kiểm tra trạng thái ngân sách được cập nhật.

Khi trình bày bài, mở `python main.py --demo`, giới thiệu bốn màn hình, thêm một giao dịch, minh họa cảnh báo, xem biểu đồ và xuất CSV. Ghi lại kết quả chạy thực tế và chụp giao diện để đưa vào báo cáo.

## 6. Đánh giá và hướng phát triển

**Ưu điểm:** Cài đặt đơn giản, chạy ngoại tuyến, dữ liệu được lưu sau khi đóng chương trình, có kiểm tra đầu vào, có thống kê trực quan và có thể xuất CSV. Cấu trúc module phù hợp để giải thích vai trò của Python trong bài toán thực tế.

**Hạn chế:** Ứng dụng dành cho một người dùng trên một máy; chưa có đồng bộ điện thoại, đăng nhập, mã hóa cơ sở dữ liệu, nhập sao kê ngân hàng, giao dịch định kỳ hoặc chia sẻ chi tiêu nhóm. Danh mục được định sẵn. Ngân sách cần đặt cho từng tháng và cảnh báo chỉ xuất hiện khi dùng ứng dụng.

**Hướng phát triển:** Cho phép tạo danh mục riêng, sao lưu và khôi phục qua giao diện, ghi nhận khoản định kỳ, nhập CSV có kiểm tra dữ liệu và so sánh mức chi giữa nhiều tháng.

Trước khi nộp bài, bổ sung tên thành viên, phân công công việc, ảnh chụp giao diện và kết quả kiểm thử thực tế theo yêu cầu của giảng viên. Mỗi thành viên nên hiểu luồng xử lý, cách tính ngân sách và phần mã mình phụ trách.
