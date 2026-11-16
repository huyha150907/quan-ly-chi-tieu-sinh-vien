"""Kiểm thử nghiệp vụ bằng cơ sở dữ liệu tạm, không đụng dữ liệu người dùng."""

import csv
import sqlite3
from datetime import date
from pathlib import Path
import tempfile
import unittest

from expense_tracker.storage import EXPENSE_CATEGORIES, ExpenseStore


class ExpenseStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.directory.name) / "expense.db"
        self.store = ExpenseStore(self.db_path)

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def expense(self, day="2026-11-16", amount=50_000, category="Ăn uống", note=""):
        return self.store.add_transaction(day, "expense", category, amount, note)

    def income(self, day="2026-11-16", amount=1_000_000, note=""):
        return self.store.add_transaction(day, "income", "Làm thêm", amount, note)

    def test_crud_and_data_survives_reopening(self):
        transaction_id = self.expense(note="  Cơm trưa  ")
        transaction = self.store.list_transactions()[0]
        self.assertEqual(transaction.id, transaction_id)
        self.assertEqual(transaction.note, "Cơm trưa")
        self.store.update_transaction(
            transaction_id, "2026-11-15", "expense", "Đi lại", 25_000, "Xe buýt"
        )
        self.store.close()
        self.store = ExpenseStore(self.db_path)
        transaction = self.store.list_transactions()[0]
        self.assertEqual(
            (transaction.date, transaction.category, transaction.amount, transaction.note),
            ("2026-11-15", "Đi lại", 25_000, "Xe buýt"),
        )
        self.store.delete_transaction(transaction_id)
        self.assertEqual(self.store.list_transactions(), [])

    def test_missing_transaction_is_reported(self):
        with self.assertRaises(ValueError):
            self.store.update_transaction(999, "2026-11-16", "expense", "Khác", 10_000)
        with self.assertRaises(ValueError):
            self.store.delete_transaction(999)

    def test_amount_must_be_positive_integer_vnd(self):
        for amount in (0, -1, 1.5, True, "10000", 1_000_000_000_001):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.expense(amount=amount)
        self.assertEqual(self.store.list_transactions(), [])

    def test_date_must_be_real_and_iso_formatted(self):
        for day in ("2026-02-29", "2026-13-01", "2026-11-31", "16/11/2026", "2026-1-1"):
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.expense(day=day)
        self.expense(day="2024-02-29")
        self.assertEqual(len(self.store.list_transactions()), 1)

    def test_type_category_and_note_validation(self):
        invalid_transactions = (
            ("2026-11-16", "other", "Khác", 10_000, ""),
            ("2026-11-16", "expense", "Làm thêm", 10_000, ""),
            ("2026-11-16", "income", "Ăn uống", 10_000, ""),
            ("2026-11-16", "expense", "Danh mục lạ", 10_000, ""),
            ("2026-11-16", "expense", "Khác", 10_000, "x" * 201),
        )
        for values in invalid_transactions:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.store.add_transaction(*values)

    def test_failed_update_preserves_existing_transaction(self):
        transaction_id = self.expense(amount=80_000, note="Dữ liệu hợp lệ")
        with self.assertRaises(ValueError):
            self.store.update_transaction(
                transaction_id, "2026-11-16", "expense", "Ăn uống", -10, "Sai"
            )
        transaction = self.store.list_transactions()[0]
        self.assertEqual((transaction.amount, transaction.note), (80_000, "Dữ liệu hợp lệ"))

    def test_sort_order_and_combined_filters(self):
        self.expense(day="2026-10-31", note="Cơm cũ")
        first_id = self.expense(day="2026-11-16", note="Cơm sáng")
        second_id = self.expense(day="2026-11-16", note="Cơm trưa")
        self.expense(day="2026-11-17", category="Đi lại", note="Xe buýt")
        self.income(day="2026-11-18")
        filtered = self.store.list_transactions(
            month="2026-11", kind="expense", category="Ăn uống", search="Cơm"
        )
        self.assertEqual([item.id for item in filtered], [second_id, first_id])

    def test_search_treats_quotes_and_sql_wildcards_as_text(self):
        expected_id = self.expense(note="Giảm 10%_ ở quán O'Brien")
        self.expense(note="Giảm 100 ở quán khác")
        self.assertEqual(
            [item.id for item in self.store.list_transactions(search="10%_")],
            [expected_id],
        )
        self.assertEqual(
            [item.id for item in self.store.list_transactions(search="O'Brien")],
            [expected_id],
        )
        self.assertEqual(self.store.list_transactions(search="' OR 1=1 --"), [])
        self.assertEqual(len(self.store.list_transactions()), 2)

    def test_summary_and_category_totals_exclude_other_months(self):
        self.income(day="2026-11-01", amount=2_000_000)
        self.expense(day="2026-11-01", amount=30_000)
        self.expense(day="2026-11-30", amount=1_200_000, category="Tiền trọ")
        self.expense(day="2026-10-31", amount=99_000)
        self.expense(day="2026-12-01", amount=88_000)
        self.assertEqual(
            self.store.summary("2026-11"),
            {"income": 2_000_000, "expense": 1_230_000, "balance": 770_000, "count": 3},
        )
        totals = self.store.category_totals("2026-11")
        self.assertEqual(set(totals), set(EXPENSE_CATEGORIES))
        self.assertEqual(totals["Ăn uống"], 30_000)
        self.assertEqual(totals["Tiền trọ"], 1_200_000)
        self.assertEqual(totals["Đi lại"], 0)
        self.assertEqual(sum(totals.values()), 1_230_000)

    def test_empty_month_has_zero_summary(self):
        self.assertEqual(
            self.store.summary("2026-01"),
            {"income": 0, "expense": 0, "balance": 0, "count": 0},
        )
        self.assertTrue(all(value == 0 for value in self.store.category_totals("2026-01").values()))

    def test_monthly_chart_crosses_year_and_fills_empty_months(self):
        self.expense(day="2025-12-31", amount=120_000)
        self.income(day="2026-01-01", amount=2_000_000)
        self.expense(day="2026-02-01", amount=30_000)
        self.assertEqual(
            self.store.monthly_totals("2026-02", count=4),
            [
                {"month": "2025-11", "income": 0, "expense": 0},
                {"month": "2025-12", "income": 0, "expense": 120_000},
                {"month": "2026-01", "income": 2_000_000, "expense": 0},
                {"month": "2026-02", "income": 0, "expense": 30_000},
            ],
        )

    def test_month_validation(self):
        for month in ("2026-00", "2026-13", "2026-1", "11/2026"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                self.store.summary(month)

    def test_budget_thresholds_and_month_category_isolation(self):
        self.store.set_budget("2026-11", "Tổng chi tiêu", 100_000)
        self.store.set_budget("2026-11", "Ăn uống", 100_000)
        self.store.set_budget("2026-10", "Ăn uống", 5_000)
        self.expense(day="2026-10-15", amount=90_000)
        self.income(amount=1_000_000)
        self.expense(amount=80_000)
        by_category = {item.category: item for item in self.store.budget_statuses("2026-11")}
        status = by_category["Ăn uống"]
        self.assertEqual((status.spent, status.remaining, status.ratio), (80_000, 20_000, 0.8))
        self.assertTrue(status.near_limit)
        self.assertFalse(status.exceeded)
        self.expense(amount=20_000, category="Đi lại")
        self.assertFalse(self.store.budget_statuses("2026-11")[0].exceeded)
        self.expense(amount=1, category="Đi lại")
        overall = self.store.budget_statuses("2026-11")[0]
        self.assertEqual(overall.category, "Tổng chi tiêu")
        self.assertTrue(overall.exceeded)
        self.assertEqual(overall.remaining, -1)
        food = {item.category: item for item in self.store.budget_statuses("2026-11")}["Ăn uống"]
        self.assertEqual(food.spent, 80_000)

    def test_budget_can_be_updated_and_removed(self):
        self.store.set_budget("2026-11", "Ăn uống", 100_000)
        self.store.set_budget("2026-11", "Ăn uống", 200_000)
        statuses = self.store.budget_statuses("2026-11")
        self.assertEqual(len(statuses), 1)
        self.assertEqual(statuses[0].limit, 200_000)
        self.store.remove_budget("2026-11", "Ăn uống")
        self.assertEqual(self.store.budget_statuses("2026-11"), [])

    def test_budget_rejects_invalid_values(self):
        for amount in (0, -1, True, 50.5):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.store.set_budget("2026-11", "Ăn uống", amount)
        with self.assertRaises(ValueError):
            self.store.set_budget("2026-11", "Làm thêm", 100_000)

    def test_available_months_includes_budgets_and_deduplicates(self):
        self.assertEqual(self.store.available_months(), [])
        self.expense(day="2026-11-01")
        self.expense(day="2026-11-15")
        self.expense(day="2025-12-31")
        self.store.set_budget("2026-11", "Ăn uống", 100_000)
        self.store.set_budget("2027-01", "Ăn uống", 100_000)
        self.assertEqual(self.store.available_months(), ["2027-01", "2026-11", "2025-12"])

    def test_batch_budgets_updates_removes_and_preserves_omitted_categories(self):
        self.store.set_budgets("2026-11", {"Ăn uống": 100_000, "Đi lại": 50_000, "Khác": 30_000})
        self.store.set_budgets("2026-10", {"Đi lại": 10_000})
        self.store.set_budgets("2026-11", {"Ăn uống": 200_000, "Đi lại": 0, "Học tập": 80_000})
        limits = {item.category: item.limit for item in self.store.budget_statuses("2026-11")}
        self.assertEqual(limits, {"Ăn uống": 200_000, "Khác": 30_000, "Học tập": 80_000})
        self.assertEqual(self.store.budget_statuses("2026-10")[0].limit, 10_000)

    def test_batch_budgets_rejects_all_invalid_inputs_before_writing(self):
        self.store.set_budget("2026-11", "Ăn uống", 100_000)
        invalid_batches = [
            {"Ăn uống": 0, "Làm thêm": 20_000},
            *({"Ăn uống": 0, "Đi lại": amount}
              for amount in (-1, True, False, 1.5, "20000", 1_000_000_000_001)),
        ]
        for amounts in invalid_batches:
            with self.subTest(amounts=amounts), self.assertRaises(ValueError):
                self.store.set_budgets("2026-11", amounts)
            self.assertEqual(
                [(item.category, item.limit) for item in self.store.budget_statuses("2026-11")],
                [("Ăn uống", 100_000)],
            )
        with self.assertRaises(ValueError):
            self.store.set_budgets("2026-13", {"Ăn uống": 0})

    def test_batch_budgets_rolls_back_deletions_if_later_write_fails(self):
        self.store.set_budget("2026-11", "Ăn uống", 100_000)
        self.store.connection.execute("""
            CREATE TRIGGER reject_transport_budget BEFORE INSERT ON budgets
            WHEN NEW.category='Đi lại'
            BEGIN SELECT RAISE(ABORT, 'test rollback'); END
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.set_budgets("2026-11", {"Ăn uống": 0, "Đi lại": 50_000})
        self.assertEqual(
            [(item.category, item.limit) for item in self.store.budget_statuses("2026-11")],
            [("Ăn uống", 100_000)],
        )

    def test_export_csv_preserves_vietnamese_and_selected_transactions(self):
        chosen_id = self.expense(note='Cơm, "trưa" ở trường')
        self.income()
        selected = [item for item in self.store.list_transactions() if item.id == chosen_id]
        target = Path(self.directory.name) / "chi_tieu.csv"
        self.assertEqual(self.store.export_csv(target, selected), 1)
        self.assertTrue(target.read_bytes().startswith(b"\xef\xbb\xbf"))
        with target.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(len(rows), 2)
        self.assertIn("Ăn uống", rows[1])
        self.assertIn('Cơm, "trưa" ở trường', rows[1])
        self.assertIn("50000", rows[1])

    def test_demo_is_repeatable_without_duplicate_rows(self):
        self.assertTrue(self.store.seed_demo(today=date(2026, 11, 16)))
        transactions = self.store.list_transactions()
        self.assertGreater(len(transactions), 0)
        self.assertTrue(self.store.budget_statuses("2026-11"))
        self.assertFalse(self.store.seed_demo(today=date(2026, 11, 16)))
        self.assertEqual(self.store.list_transactions(), transactions)
        months = {item.date[:7] for item in transactions}
        self.assertEqual(months, {"2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"})
        self.assertTrue(all(item.date <= "2026-11-16" for item in transactions))

    def test_demo_does_not_modify_existing_user_data(self):
        transaction_id = self.expense(note="Khoản chi cá nhân")
        self.assertFalse(self.store.seed_demo(today=date(2026, 11, 16)))
        self.assertEqual([item.id for item in self.store.list_transactions()], [transaction_id])
        self.assertEqual(self.store.budget_statuses("2026-11"), [])

    def test_demo_does_not_modify_existing_budgets(self):
        self.store.set_budget("2026-11", "Ăn uống", 2_000_000)
        self.assertFalse(self.store.seed_demo(today=date(2026, 11, 16)))
        self.assertEqual(self.store.list_transactions(), [])
        self.assertEqual(self.store.budget_statuses("2026-11")[0].limit, 2_000_000)


if __name__ == "__main__":
    unittest.main()
