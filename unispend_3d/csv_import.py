"""Đọc tệp xuất của UTH và CSV với các cột giao dịch cơ bản."""

import csv
import re
from datetime import date, datetime
from io import StringIO
from math import isfinite

if __package__:
    from .models import EXPENSE_CATEGORIES, INCOME_CATEGORIES, Transaction
else:
    from models import EXPENSE_CATEGORIES, INCOME_CATEGORIES, Transaction


ALIASES = {
    "Ngày giao dịch": "date", "Ngày": "date",
    "Loại giao dịch": "tx_type", "Loại": "tx_type",
    "Danh mục": "category",
    "Số tiền (VNĐ)": "amount", "Số tiền": "amount",
    "Ghi chú chi tiết": "note", "Ghi chú": "note",
}
REQUIRED = {"date", "tx_type", "category", "amount"}
CATEGORIES = {"Chi tiêu": EXPENSE_CATEGORIES, "Thu nhập": INCOME_CATEGORIES}
REPORT_TOTALS = {"TỔNG THU", "TỔNG CHI", "CHÊNH LỆCH"}


def read_transactions_csv(content: bytes) -> list[Transaction]:
    reader = csv.DictReader(StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    columns = [ALIASES.get(name.strip(), name.strip()) for name in reader.fieldnames or []]
    if not REQUIRED <= set(columns) or len(columns) != len(set(columns)):
        raise ValueError("CSV thiếu hoặc trùng cột Ngày giao dịch, Loại giao dịch, Danh mục hoặc Số tiền (VNĐ).")
    reader.fieldnames = columns
    transactions = []
    for row in reader:
        tx_type = (row["tx_type"] or "").strip()
        if tx_type in REPORT_TOTALS and not row["date"]:
            continue
        try:
            if None in row:
                raise ValueError("Dòng có nhiều ô hơn tiêu đề cột.")
            raw_date = (row["date"] or "").strip()
            day = datetime.strptime(raw_date, "%d/%m/%Y").date() if "/" in raw_date else date.fromisoformat(raw_date)
            category = (row["category"] or "").strip()
            if tx_type not in CATEGORIES or category not in CATEGORIES[tx_type]:
                raise ValueError("Loại giao dịch hoặc danh mục không hợp lệ.")
            raw_amount = re.sub(r"[\sđ₫]", "", row["amount"] or "")
            if re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]{1,3}(?:,[0-9]{3})+", raw_amount):
                raw_amount = raw_amount.replace(".", "").replace(",", "")
            amount = float(raw_amount.replace(",", "."))
            if not isfinite(amount):
                raise ValueError("Số tiền không hợp lệ.")
            note = (row.get("note") or "").strip() or f"{category} ({day.isoformat()})"
            tx = Transaction(0, day.isoformat(), tx_type, category, amount, note)
            valid, message = tx.validate()
            if not valid:
                raise ValueError(message)
        except ValueError as exc:
            raise ValueError(f"Dòng {reader.line_num} không hợp lệ. {exc}") from exc
        transactions.append(tx)
    return transactions
