"""Lưu trữ, kiểm tra dữ liệu và tính toán thu chi bằng SQLite.

Tiền được lưu bằng số nguyên đồng Việt Nam để tránh sai số số thực.
Các truy vấn nhận dữ liệu từ người dùng đều dùng tham số SQL.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import dataclass
from datetime import date as Date
from pathlib import Path
from typing import Iterable


EXPENSE_CATEGORIES = ("Ăn uống", "Tiền trọ", "Đi lại", "Học tập", "Giải trí", "Khác")
INCOME_CATEGORIES = ("Gia đình hỗ trợ", "Làm thêm", "Học bổng", "Khác")
TYPE_LABELS = {"expense": "Chi tiêu", "income": "Thu nhập"}
TOTAL_BUDGET_CATEGORY = "Tổng chi tiêu"
MAX_AMOUNT = 1_000_000_000_000


@dataclass(frozen=True)
class Transaction:
    id: int
    date: str
    kind: str
    category: str
    amount: int
    note: str


@dataclass(frozen=True)
class BudgetStatus:
    category: str
    limit: int
    spent: int

    @property
    def remaining(self) -> int:
        return self.limit - self.spent

    @property
    def ratio(self) -> float:
        return self.spent / self.limit

    @property
    def exceeded(self) -> bool:
        return self.spent > self.limit

    @property
    def near_limit(self) -> bool:
        return self.spent * 5 >= self.limit * 4


def _month(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
        raise ValueError("Tháng phải có dạng YYYY-MM.")
    try:
        Date.fromisoformat(value + "-01")
    except ValueError:
        raise ValueError("Tháng không hợp lệ.") from None
    return value


def _date(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Ngày phải có dạng YYYY-MM-DD.")
    try:
        Date.fromisoformat(value)
    except ValueError:
        raise ValueError("Ngày không hợp lệ.") from None
    return value


def _amount(value: int) -> int:
    if type(value) is not int or not 0 < value <= MAX_AMOUNT:
        raise ValueError("Số tiền phải là số nguyên dương, tối đa 1.000 tỷ đồng.")
    return value


def _budget_category(value: str) -> str:
    if value != TOTAL_BUDGET_CATEGORY and value not in EXPENSE_CATEGORIES:
        raise ValueError("Danh mục ngân sách không hợp lệ.")
    return value


def _transaction_values(date: str, kind: str, category: str, amount: int, note: str):
    _date(date)
    if kind not in TYPE_LABELS:
        raise ValueError("Loại giao dịch không hợp lệ.")
    categories = EXPENSE_CATEGORIES if kind == "expense" else INCOME_CATEGORIES
    if category not in categories:
        raise ValueError("Danh mục không phù hợp với loại giao dịch.")
    _amount(amount)
    if not isinstance(note, str):
        raise ValueError("Ghi chú phải là văn bản.")
    note = note.strip()
    if len(note) > 200:
        raise ValueError("Ghi chú không được dài quá 200 ký tự.")
    return date, kind, category, amount, note


def _month_range(end_month: str, count: int) -> list[str]:
    _month(end_month)
    if type(count) is not int or not 1 <= count <= 120:
        raise ValueError("Số tháng phải từ 1 đến 120.")
    year, month = map(int, end_month.split("-"))
    end = (year - 1) * 12 + month - 1
    if end - count + 1 < 0:
        raise ValueError("Khoảng tháng nằm ngoài phạm vi hỗ trợ.")
    return [f"{index // 12 + 1:04d}-{index % 12 + 1:02d}"
            for index in range(end - count + 1, end + 1)]


class ExpenseStore:
    """Một cơ sở dữ liệu cục bộ cho một người sử dụng."""

    def __init__(self, db_path: str | Path):
        if str(db_path) != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(db_path))
        self.connection.row_factory = sqlite3.Row
        with self.connection:
            self.connection.executescript("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL CHECK(length(date) = 10),
                    kind TEXT NOT NULL CHECK(kind IN ('income', 'expense')),
                    category TEXT NOT NULL,
                    amount INTEGER NOT NULL
                        CHECK(typeof(amount) = 'integer' AND amount > 0 AND amount <= 1000000000000),
                    note TEXT NOT NULL DEFAULT '' CHECK(length(note) <= 200),
                    CHECK(
                        (kind = 'expense' AND category IN
                         ('Ăn uống', 'Tiền trọ', 'Đi lại', 'Học tập', 'Giải trí', 'Khác'))
                        OR
                        (kind = 'income' AND category IN
                         ('Gia đình hỗ trợ', 'Làm thêm', 'Học bổng', 'Khác'))
                    )
                );
                CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
                CREATE TABLE IF NOT EXISTS budgets (
                    month TEXT NOT NULL CHECK(length(month) = 7),
                    category TEXT NOT NULL CHECK(category IN
                        ('Tổng chi tiêu', 'Ăn uống', 'Tiền trọ', 'Đi lại', 'Học tập', 'Giải trí', 'Khác')),
                    amount INTEGER NOT NULL
                        CHECK(typeof(amount) = 'integer' AND amount > 0 AND amount <= 1000000000000),
                    PRIMARY KEY(month, category)
                );
            """)

    def close(self) -> None:
        self.connection.close()

    def add_transaction(self, date: str, kind: str, category: str, amount: int, note: str = "") -> int:
        values = _transaction_values(date, kind, category, amount, note)
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO transactions(date, kind, category, amount, note) VALUES (?, ?, ?, ?, ?)",
                values,
            )
        return int(cursor.lastrowid)

    def update_transaction(self, transaction_id: int, date: str, kind: str,
                           category: str, amount: int, note: str = "") -> None:
        values = _transaction_values(date, kind, category, amount, note)
        self._validate_id(transaction_id)
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE transactions SET date=?, kind=?, category=?, amount=?, note=? WHERE id=?",
                (*values, transaction_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Không tìm thấy giao dịch.")

    @staticmethod
    def _validate_id(transaction_id: int) -> None:
        if type(transaction_id) is not int or transaction_id <= 0:
            raise ValueError("Mã giao dịch không hợp lệ.")

    def delete_transaction(self, transaction_id: int) -> None:
        self._validate_id(transaction_id)
        with self.connection:
            cursor = self.connection.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            if cursor.rowcount == 0:
                raise ValueError("Không tìm thấy giao dịch.")

    def list_transactions(self, month: str | None = None, kind: str | None = None,
                          category: str | None = None, search: str = "") -> list[Transaction]:
        clauses, parameters = [], []
        if month is not None:
            _month(month)
            clauses.append("substr(date, 1, 7) = ?")
            parameters.append(month)
        if kind is not None:
            if kind not in TYPE_LABELS:
                raise ValueError("Loại giao dịch không hợp lệ.")
            clauses.append("kind = ?")
            parameters.append(kind)
        if category is not None:
            if category not in EXPENSE_CATEGORIES + INCOME_CATEGORIES:
                raise ValueError("Danh mục không hợp lệ.")
            clauses.append("category = ?")
            parameters.append(category)
        if not isinstance(search, str):
            raise ValueError("Từ khóa phải là văn bản.")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.connection.execute(
            "SELECT id, date, kind, category, amount, note FROM transactions" + where +
            " ORDER BY date DESC, id DESC", parameters,
        ).fetchall()
        # casefold hỗ trợ chữ tiếng Việt tốt hơn LIKE mặc định của SQLite.
        keyword = search.strip().casefold()
        return [Transaction(**dict(row)) for row in rows
                if not keyword or keyword in (row["note"] + " " + row["category"]).casefold()]

    def summary(self, month: str) -> dict[str, int]:
        _month(month)
        row = self.connection.execute("""
            SELECT COALESCE(SUM(CASE WHEN kind='income' THEN amount ELSE 0 END), 0) AS income,
                   COALESCE(SUM(CASE WHEN kind='expense' THEN amount ELSE 0 END), 0) AS expense,
                   COUNT(*) AS count
            FROM transactions WHERE substr(date, 1, 7)=?
        """, (month,)).fetchone()
        return {"income": row["income"], "expense": row["expense"],
                "balance": row["income"] - row["expense"], "count": row["count"]}

    def category_totals(self, month: str) -> dict[str, int]:
        _month(month)
        totals = dict.fromkeys(EXPENSE_CATEGORIES, 0)
        rows = self.connection.execute("""
            SELECT category, SUM(amount) AS total FROM transactions
            WHERE kind='expense' AND substr(date, 1, 7)=? GROUP BY category
        """, (month,)).fetchall()
        totals.update({row["category"]: row["total"] for row in rows})
        return totals

    def monthly_totals(self, end_month: str, count: int = 6) -> list[dict[str, int | str]]:
        months = _month_range(end_month, count)
        rows = self.connection.execute("""
            SELECT substr(date, 1, 7) AS month,
                   SUM(CASE WHEN kind='income' THEN amount ELSE 0 END) AS income,
                   SUM(CASE WHEN kind='expense' THEN amount ELSE 0 END) AS expense
            FROM transactions WHERE substr(date, 1, 7) BETWEEN ? AND ?
            GROUP BY substr(date, 1, 7)
        """, (months[0], months[-1])).fetchall()
        indexed = {row["month"]: dict(row) for row in rows}
        return [indexed.get(month, {"month": month, "income": 0, "expense": 0}) for month in months]

    def set_budget(self, month: str, category: str, amount: int) -> None:
        _month(month)
        _budget_category(category)
        _amount(amount)
        with self.connection:
            self.connection.execute("""
                INSERT INTO budgets(month, category, amount) VALUES (?, ?, ?)
                ON CONFLICT(month, category) DO UPDATE SET amount=excluded.amount
            """, (month, category, amount))

    def remove_budget(self, month: str, category: str) -> None:
        _month(month)
        _budget_category(category)
        with self.connection:
            self.connection.execute("DELETE FROM budgets WHERE month=? AND category=?", (month, category))

    def budget_statuses(self, month: str) -> list[BudgetStatus]:
        _month(month)
        totals = self.category_totals(month)
        totals[TOTAL_BUDGET_CATEGORY] = sum(totals.values())
        budgets = {row["category"]: row["amount"] for row in self.connection.execute(
            "SELECT category, amount FROM budgets WHERE month=?", (month,))}
        return [BudgetStatus(category, budgets[category], totals[category])
                for category in (TOTAL_BUDGET_CATEGORY, *EXPENSE_CATEGORIES) if category in budgets]

    def export_csv(self, path: str | Path, transactions: Iterable[Transaction] | None = None) -> int:
        records = list(self.list_transactions() if transactions is None else transactions)
        with open(path, "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("Mã", "Ngày", "Loại", "Danh mục", "Số tiền (VNĐ)", "Ghi chú"))
            for record in records:
                # Ngăn ghi chú được phần mềm bảng tính hiểu thành công thức.
                note = record.note
                if note.lstrip().startswith(("=", "+", "-", "@")):
                    note = "'" + note
                writer.writerow((record.id, record.date, TYPE_LABELS[record.kind],
                                 record.category, record.amount, note))
        return len(records)

    def seed_demo(self, today: Date | None = None) -> bool:
        """Tạo dữ liệu minh họa một lần, tuyệt đối không trộn vào dữ liệu đã có."""
        today = Date.today() if today is None else today
        if not isinstance(today, Date):
            raise ValueError("Ngày tạo dữ liệu mẫu không hợp lệ.")
        has_data = self.connection.execute("SELECT EXISTS(SELECT 1 FROM transactions)").fetchone()[0]
        has_budgets = self.connection.execute("SELECT EXISTS(SELECT 1 FROM budgets)").fetchone()[0]
        if has_data or has_budgets:
            return False
        months = _month_range(today.strftime("%Y-%m"), 6)
        sample_expenses = (
            (1, "Tiền trọ", 2_200_000, "Tiền phòng và điện nước"),
            (2, "Ăn uống", 280_000, "Mua thực phẩm đầu tháng"),
            (4, "Đi lại", 100_000, "Đổ xăng"),
            (5, "Ăn uống", 350_000, "Cơm trưa tuần 1"),
            (6, "Học tập", 180_000, "Giáo trình và in tài liệu"),
            (8, "Ăn uống", 320_000, "Cơm trưa tuần 2"),
            (9, "Giải trí", 120_000, "Xem phim cùng bạn"),
            (11, "Đi lại", 100_000, "Vé xe buýt và xăng"),
            (12, "Ăn uống", 290_000, "Thực phẩm cuối tuần"),
            (14, "Khác", 90_000, "Đồ dùng sinh hoạt"),
            (15, "Ăn uống", 250_000, "Cơm trưa tuần 3"),
            (16, "Đi lại", 100_000, "Đổ xăng"),
        )
        records = []
        for offset, month in enumerate(months):
            max_day = today.day if month == today.strftime("%Y-%m") else 28

            def sample_date(day: int) -> str:
                return f"{month}-{min(day, max_day):02d}"

            records.extend((
                (sample_date(1), "income", "Gia đình hỗ trợ", 4_500_000, "Gia đình gửi sinh hoạt phí"),
                (sample_date(10), "income", "Làm thêm", 1_500_000, "Lương làm thêm"),
            ))
            for day, category, amount, note in sample_expenses:
                adjustment = (offset - 5) * 10_000 if category != "Tiền trọ" else 0
                records.append((sample_date(day), "expense", category, amount + adjustment, note))
        with self.connection:
            self.connection.executemany(
                "INSERT INTO transactions(date, kind, category, amount, note) VALUES (?, ?, ?, ?, ?)", records)
            self.connection.executemany(
                "INSERT INTO budgets(month, category, amount) VALUES (?, ?, ?)",
                ((today.strftime("%Y-%m"), TOTAL_BUDGET_CATEGORY, 4_300_000),
                 (today.strftime("%Y-%m"), "Ăn uống", 1_200_000),
                 (today.strftime("%Y-%m"), "Đi lại", 400_000)),
            )
        return True
