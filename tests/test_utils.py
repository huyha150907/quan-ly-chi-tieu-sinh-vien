"""Kiểm thử cách đọc tiền VND và chuyển tháng trước khi dữ liệu vào giao diện."""

import unittest

from expense_tracker.utils import money, parse_amount, shift_month, validate_month


class AmountTests(unittest.TestCase):
    def test_accepts_plain_integer_and_consistent_thousands_grouping(self):
        cases = {
            "1": 1,
            "50000": 50_000,
            "  50000  ": 50_000,
            "50.000": 50_000,
            "50,000": 50_000,
            "50 000": 50_000,
            "1.200.000": 1_200_000,
            "1,200,000": 1_200_000,
            "1 200 000": 1_200_000,
            "1000000000000": 1_000_000_000_000,
            "1.000.000.000.000": 1_000_000_000_000,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_amount(text), expected)

    def test_rejects_fractional_or_inconsistent_grouping(self):
        # Các giá trị này không được âm thầm xóa dấu rồi biến thành tiền lớn hơn.
        for text in (
            "1.5", "1,5", "12.34", "12,34", "1.000,50", "1,000.50",
            "1.200,000", "1,200.000", "1 200.000", "1.200 000",
            "1.0000", "10.00", "1000.000", "01.000", "1..000", "1  000",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_amount(text)

    def test_rejects_zero_negative_nonnumeric_and_excessive_amounts(self):
        for text in (
            "", " ", "0", "000", "-1", "-50.000", "+50000", "50k",
            "50.000 đ", "1e6", "NaN", "1000000000001", "1.000.000.000.001",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_amount(text)

    def test_formats_vnd_with_dots_and_preserves_negative_balance(self):
        for amount, expected in (
            (0, "0 đ"), (1, "1 đ"), (50_000, "50.000 đ"),
            (1_200_000, "1.200.000 đ"), (-25_000, "-25.000 đ"),
        ):
            with self.subTest(amount=amount):
                self.assertEqual(money(amount), expected)


class MonthTests(unittest.TestCase):
    def test_validates_calendar_month_and_returns_it(self):
        for month in ("0001-01", "2024-02", "2026-11", "9999-12"):
            with self.subTest(month=month):
                self.assertEqual(validate_month(month), month)

    def test_rejects_invalid_or_noncanonical_months(self):
        for month in (
            "0000-01", "10000-01", "2026-00", "2026-13", "2026-1",
            "26-11", "11/2026", "2026-11-01", " 2026-11", "2026-11 ", "",
        ):
            with self.subTest(month=month), self.assertRaises(ValueError):
                validate_month(month)

    def test_shift_crosses_years_in_both_directions(self):
        for month, offset, expected in (
            ("2026-12", 1, "2027-01"),
            ("2026-01", -1, "2025-12"),
            ("2026-11", 0, "2026-11"),
            ("2026-11", 14, "2028-01"),
            ("2026-02", -14, "2024-12"),
            ("0001-01", 12, "0002-01"),
            ("9999-12", -12, "9998-12"),
        ):
            with self.subTest(month=month, offset=offset):
                self.assertEqual(shift_month(month, offset), expected)

    def test_shift_reports_supported_year_boundaries(self):
        for month, offset in (("0001-01", -1), ("9999-12", 1), ("2026-11", 120_000)):
            with self.subTest(month=month, offset=offset), self.assertRaises(ValueError):
                shift_month(month, offset)
        self.assertEqual(shift_month("0001-01", 0), "0001-01")
        self.assertEqual(shift_month("9999-12", 0), "9999-12")


if __name__ == "__main__":
    unittest.main()
