"""Kiểm tra số liệu biểu đồ độc lập với trình duyệt."""

import unittest

from expense_tracker.charts import _daily_expense_rows, _monthly_category_rows
from expense_tracker.storage import Transaction


class ChartDataTests(unittest.TestCase):
    def test_monthly_totals_filter_income_and_dates_and_keep_zero_months(self):
        records = [
            Transaction(1, "2026-11-01", "expense", "Ăn uống", 45_000, ""),
            Transaction(2, "2026-11-02", "expense", "Ăn uống", 55_000, ""),
            Transaction(3, "2026-11-03", "income", "Khác", 1_000_000, ""),
            Transaction(4, "2026-09-01", "expense", "Ăn uống", 99_000, ""),
        ]
        rows = _monthly_category_rows(records, ["2026-10", "2026-11"])
        indexed = {(row["month"], row["category"]): row["amount"] for row in rows}
        self.assertEqual(len(rows), 12)
        self.assertEqual(indexed["2026-11", "Ăn uống"], 100_000)
        self.assertEqual(indexed["2026-10", "Ăn uống"], 0)
        self.assertEqual(indexed["2026-11", "Khác"], 0)
        self.assertEqual(sum(row["amount"] for row in rows), 100_000)
        self.assertTrue(all(type(row["amount"]) is int for row in rows))

    def test_daily_totals_fill_leap_month_and_ignore_income(self):
        records = [
            Transaction(1, "2024-02-29", "expense", "Ăn uống", 30_000, ""),
            Transaction(2, "2024-02-29", "expense", "Đi lại", 20_000, ""),
            Transaction(3, "2024-02-29", "income", "Làm thêm", 1_000_000, ""),
            Transaction(4, "2024-03-01", "expense", "Ăn uống", 99_000, ""),
        ]
        rows = _daily_expense_rows(records, "2024-02")
        self.assertEqual(len(rows), 29)
        self.assertEqual(rows[0], {"date": "2024-02-01", "amount": 0})
        self.assertEqual(rows[-1], {"date": "2024-02-29", "amount": 50_000})
        self.assertEqual(sum(row["amount"] for row in rows), 50_000)

    def test_daily_rows_validate_month(self):
        with self.assertRaises(ValueError):
            _daily_expense_rows([], "2026-13")


if __name__ == "__main__":
    unittest.main()
