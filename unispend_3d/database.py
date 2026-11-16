# -*- coding: utf-8 -*-
"""
Module database.py
Quản lý kết nối cơ sở dữ liệu SQLite3, thực hiện các thao tác CRUD (Thêm, Đọc, Sửa, Xóa),
thống kê bằng Pandas và khởi tạo dữ liệu mẫu thông minh cho sinh viên.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from models import Transaction, BudgetConfig, EXPENSE_CATEGORIES


class ExpenseDatabase:
    """
    Lớp quản lý cơ sở dữ liệu SQLite cho Ứng dụng Quản lý Chi tiêu Sinh viên.
    """

    def __init__(self, db_path: str = "data/student_expense.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()
        self._seed_sample_data_if_empty()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        """Tạo các bảng dữ liệu nếu chưa tồn tại."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Bảng giao dịch thu/chi
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    tx_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    note TEXT
                )
            """)
            # Bảng cấu hình ngân sách theo tháng
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    month TEXT PRIMARY KEY,
                    total_budget REAL NOT NULL,
                    category_limits_json TEXT NOT NULL
                )
            """)
            conn.commit()

    def _seed_sample_data_if_empty(self) -> None:
        """
        Tự động tạo dữ liệu mẫu đa dạng (trong 4 tháng gần nhất) nếu DB đang trống,
        giúp giảng viên và sinh viên chạy thử có ngay biểu đồ đẹp để đánh giá.
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM transactions")
            count = cursor.fetchone()["cnt"]
            if count > 0:
                return

        self.reset_to_sample_data()

    def reset_to_sample_data(self) -> None:
        """Xóa dữ liệu cũ và nạp lại bộ dữ liệu mẫu thực tế của sinh viên."""
        now = datetime.now()
        y = now.year
        m = now.month

        def get_ym(offset_months: int) -> str:
            total_m = (y * 12 + (m - 1)) + offset_months
            ny = total_m // 12
            nm = (total_m % 12) + 1
            return f"{ny:04d}-{nm:02d}"

        m_curr = get_ym(0)   # Tháng hiện tại
        m_prev1 = get_ym(-1) # 1 tháng trước
        m_prev2 = get_ym(-2) # 2 tháng trước
        m_prev3 = get_ym(-3) # 3 tháng trước

        sample_txs = [
            # --- 3 THÁNG TRƯỚC ---
            (f"{m_prev3}-01", "Thu nhập", "Trợ cấp gia đình", 4500000, "Bố mẹ gửi tiền sinh hoạt đầu tháng"),
            (f"{m_prev3}-05", "Thu nhập", "Làm thêm (Part-time)", 1500000, "Lương gia sư Toán lớp 9"),
            (f"{m_prev3}-02", "Chi tiêu", "Tiền trọ", 1800000, "Tiền phòng trọ + điện nước + wifi"),
            (f"{m_prev3}-04", "Chi tiêu", "Tiền ăn", 650000, "Đi chợ nấu ăn tuần 1 & mua gạo"),
            (f"{m_prev3}-08", "Chi tiêu", "Đi lại", 180000, "Đổ xăng xe máy + vé gửi xe trường"),
            (f"{m_prev3}-12", "Chi tiêu", "Học tập", 320000, "Mua giáo trình Python & in tài liệu ôn thi"),
            (f"{m_prev3}-15", "Chi tiêu", "Tiền ăn", 720000, "Tiền ăn trưa căn tin & ăn tối tuần 2-3"),
            (f"{m_prev3}-20", "Chi tiêu", "Đi lại", 140000, "Đổ xăng + đi Grab hôm mưa"),
            (f"{m_prev3}-24", "Chi tiêu", "Tiền ăn", 580000, "Tiền ăn cuối tháng + liên hoan nhóm"),
            (f"{m_prev3}-26", "Chi tiêu", "Giải trí & Xã giao", 250000, "Xem phim CGV & cà phê với bạn"),

            # --- 2 THÁNG TRƯỚC ---
            (f"{m_prev2}-01", "Thu nhập", "Trợ cấp gia đình", 4500000, "Trợ cấp gia đình hàng tháng"),
            (f"{m_prev2}-06", "Thu nhập", "Làm thêm (Part-time)", 1800000, "Lương làm thêm quán cà phê"),
            (f"{m_prev2}-03", "Chi tiêu", "Tiền trọ", 1850000, "Tiền phòng + điện điều hòa tăng"),
            (f"{m_prev2}-05", "Chi tiêu", "Tiền ăn", 750000, "Ăn uống tuần 1 + mua đồ khô dự trữ"),
            (f"{m_prev2}-09", "Chi tiêu", "Đi lại", 210000, "Đổ xăng + thay dầu nhớt xe máy"),
            (f"{m_prev2}-14", "Chi tiêu", "Tiền ăn", 690000, "Ăn cơm suất sinh viên & trà sữa"),
            (f"{m_prev2}-18", "Chi tiêu", "Sinh hoạt & Mua sắm", 420000, "Mua áo sơ mi + đồ dùng sinh hoạt"),
            (f"{m_prev2}-22", "Chi tiêu", "Tiền ăn", 680000, "Đi siêu thị Co.opmart mua thức ăn"),
            (f"{m_prev2}-25", "Chi tiêu", "Đi lại", 150000, "Vé xe khách về quê thăm nhà"),
            (f"{m_prev2}-28", "Chi tiêu", "Học tập", 200000, "Đăng ký khóa học online Coursera"),

            # --- 1 THÁNG TRƯỚC ---
            (f"{m_prev1}-01", "Thu nhập", "Trợ cấp gia đình", 4500000, "Bố mẹ chuyển khoản đầu tháng"),
            (f"{m_prev1}-07", "Thu nhập", "Làm thêm (Part-time)", 1600000, "Lương gia sư + trợ giảng"),
            (f"{m_prev1}-15", "Thu nhập", "Học bổng & Thưởng", 1000000, "Thưởng nghiên cứu khoa học sinh viên"),
            (f"{m_prev1}-02", "Chi tiêu", "Tiền trọ", 1800000, "Tiền thuê trọ + điện nước tháng trước"),
            (f"{m_prev1}-05", "Chi tiêu", "Tiền ăn", 820000, "Tiền ăn tuần 1 + lẩu cuối tuần"),
            (f"{m_prev1}-10", "Chi tiêu", "Đi lại", 190000, "Đổ xăng RON 95 + gửi xe tháng"),
            (f"{m_prev1}-14", "Chi tiêu", "Tiền ăn", 760000, "Cơm trưa ở trường + nấu ăn tối"),
            (f"{m_prev1}-19", "Chi tiêu", "Học tập", 450000, "Đóng lệ phí thi chứng chỉ tiếng Anh"),
            (f"{m_prev1}-22", "Chi tiêu", "Đi lại", 170000, "Đổ xăng & đi xe buýt"),
            (f"{m_prev1}-25", "Chi tiêu", "Tiền ăn", 640000, "Mua đồ ăn tuần cuối tháng"),
            (f"{m_prev1}-27", "Chi tiêu", "Giải trí & Xã giao", 350000, "Quà sinh nhật bạn cùng phòng"),

            # --- THÁNG HIỆN TẠI (Có mục chạm/vượt ngưỡng để demo Cảnh báo ngân sách) ---
            (f"{m_curr}-01", "Thu nhập", "Trợ cấp gia đình", 4500000, "Bố mẹ gửi tiền tháng này"),
            (f"{m_curr}-05", "Thu nhập", "Làm thêm (Part-time)", 1800000, "Lương làm thêm part-time"),
            (f"{m_curr}-02", "Chi tiêu", "Tiền trọ", 1850000, "Tiền nhà trọ (1.5tr) + Điện nước Wifi (350k)"),
            (f"{m_curr}-03", "Chi tiêu", "Tiền ăn", 480000, "Đi siêu thị mua thịt, cá, rau tuần 1"),
            (f"{m_curr}-05", "Chi tiêu", "Đi lại", 150000, "Đổ đầy bình xăng + vé gửi xe tháng ở trường"),
            (f"{m_curr}-07", "Chi tiêu", "Tiền ăn", 520000, "Ăn trưa căn tin trường & uống trà sữa nhóm BTL"),
            (f"{m_curr}-09", "Chi tiêu", "Học tập", 280000, "In báo cáo Bài tập lớn Python & mua sách tham khảo"),
            (f"{m_curr}-11", "Chi tiêu", "Đi lại", 220000, "Thay săm lốp xe máy + đổ xăng"),
            (f"{m_curr}-13", "Chi tiêu", "Tiền ăn", 690000, "Liên hoan nhóm làm đồ án + ăn uống tuần 2"),
            (f"{m_curr}-14", "Chi tiêu", "Sinh hoạt & Mua sắm", 350000, "Mua đồ dùng cá nhân & bột giặt"),
            (f"{m_curr}-15", "Chi tiêu", "Tiền ăn", 460000, "Mua đồ nấu ăn tuần 3 (Vượt định mức Tiền ăn!)"),
            (f"{m_curr}-16", "Chi tiêu", "Đi lại", 95000, "Đặt GrabBike đi học hôm trời mưa to"),
            (f"{m_curr}-16", "Chi tiêu", "Giải trí & Xã giao", 240000, "Cà phê họp nhóm làm slide thuyết trình"),
        ]

        default_limits = {
            "Tiền ăn": 2000000.0,            # Đã tiêu 2,150,000 -> VƯỢT NGÂN SÁCH (107.5%)
            "Tiền trọ": 1900000.0,           # Đã tiêu 1,850,000 -> SẮP CHẠM NGƯỠNG (97.4%)
            "Đi lại": 500000.0,              # Đã tiêu 465,000   -> SẮP CHẠM NGƯỠNG (93.0%)
            "Học tập": 500000.0,
            "Sinh hoạt & Mua sắm": 400000.0,
            "Giải trí & Xã giao": 300000.0,
            "Chi phí khác": 200000.0,
        }

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions")
            cursor.execute("DELETE FROM budgets")

            cursor.executemany("""
                INSERT INTO transactions (date, tx_type, category, amount, note)
                VALUES (?, ?, ?, ?, ?)
            """, sample_txs)

            for m_key in [m_prev3, m_prev2, m_prev1, m_curr]:
                cursor.execute("""
                    INSERT INTO budgets (month, total_budget, category_limits_json)
                    VALUES (?, ?, ?)
                """, (m_key, 5500000.0, json.dumps(default_limits, ensure_ascii=False)))

            conn.commit()

    # =========================================================================
    # CÁC PHƯƠNG THỨC THAO TÁC DỮ LIỆU (CRUD)
    # =========================================================================

    def add_transaction(self, tx: Transaction) -> tuple[bool, str]:
        """Thêm một khoản thu/chi mới sau khi kiểm tra lỗi dữ liệu đầu vào."""
        is_valid, msg = tx.validate()
        if not is_valid:
            return False, msg

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (date, tx_type, category, amount, note)
                VALUES (?, ?, ?, ?, ?)
            """, (tx.date, tx.tx_type, tx.category, tx.amount, tx.note.strip()))
            conn.commit()
        return True, "Đã lưu giao dịch thành công!"

    def delete_transaction(self, tx_id: int) -> bool:
        """Xóa một giao dịch theo ID."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_transactions_df(self, month: Optional[str] = None) -> pd.DataFrame:
        """
        Đọc danh sách giao dịch ra Pandas DataFrame để phục vụ thống kê và vẽ biểu đồ.
        Nếu truyền `month` (YYYY-MM), lọc riêng tháng đó.
        """
        with self._get_conn() as conn:
            if month:
                query = "SELECT * FROM transactions WHERE substr(date, 1, 7) = ? ORDER BY date DESC, id DESC"
                df = pd.read_sql_query(query, conn, params=(month,))
            else:
                query = "SELECT * FROM transactions ORDER BY date DESC, id DESC"
                df = pd.read_sql_query(query, conn)

        if not df.empty:
            df["month"] = df["date"].str.slice(0, 7)
            df["amount"] = df["amount"].astype(float)
        else:
            df = pd.DataFrame(columns=["id", "date", "tx_type", "category", "amount", "note", "month"])
        return df

    def get_available_months(self) -> List[str]:
        """Lấy danh sách các tháng (YYYY-MM) đang có dữ liệu."""
        curr_m = datetime.now().strftime("%Y-%m")
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT substr(date, 1, 7) as m FROM transactions ORDER BY m DESC")
            months = [row["m"] for row in cursor.fetchall() if row["m"]]
        if curr_m not in months:
            months.insert(0, curr_m)
        return sorted(list(set(months)), reverse=True)

    # =========================================================================
    # QUẢN LÝ NGÂN SÁCH & CẢNH BÁO
    # =========================================================================

    def get_budget_config(self, month: str) -> BudgetConfig:
        """Lấy cấu hình ngân sách của tháng `month`. Nếu chưa có thì trả về mặc định."""
        default_limits = {
            "Tiền ăn": 2000000.0,
            "Tiền trọ": 1900000.0,
            "Đi lại": 500000.0,
            "Học tập": 500000.0,
            "Sinh hoạt & Mua sắm": 400000.0,
            "Giải trí & Xã giao": 300000.0,
            "Chi phí khác": 200000.0,
        }
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM budgets WHERE month = ?", (month,))
            row = cursor.fetchone()
            if row:
                limits = json.loads(row["category_limits_json"])
                for cat in EXPENSE_CATEGORIES:
                    if cat not in limits:
                        limits[cat] = default_limits.get(cat, 300000.0)
                return BudgetConfig(
                    month=month,
                    total_budget=float(row["total_budget"]),
                    category_limits=limits
                )
        return BudgetConfig(month=month, total_budget=5500000.0, category_limits=default_limits)

    def save_budget_config(self, config: BudgetConfig) -> None:
        """Lưu hoặc cập nhật định mức ngân sách tháng."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO budgets (month, total_budget, category_limits_json)
                VALUES (?, ?, ?)
                ON CONFLICT(month) DO UPDATE SET
                    total_budget = excluded.total_budget,
                    category_limits_json = excluded.category_limits_json
            """, (config.month, config.total_budget, json.dumps(config.category_limits, ensure_ascii=False)))
            conn.commit()
