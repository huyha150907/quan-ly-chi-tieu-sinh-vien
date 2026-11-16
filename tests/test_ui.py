"""Kiểm tra luồng nhập liệu Streamlit bằng SQLite tạm, không dùng data/ cá nhân."""

import csv
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from expense_tracker.storage import ExpenseStore, TOTAL_BUDGET_CATEGORY
from expense_tracker.ui import _csv_bytes


class ExpenseUiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_path = Path(self.directory.name) / "ui.db"
        self.today = date.today()
        self.month = self.today.strftime("%Y-%m")

    def open_app(self, demo=False):
        source = (
            "from pathlib import Path\n"
            "from expense_tracker.ui import run_app\n"
            f"run_app(Path({str(self.db_path)!r}), demo={demo!r})\n"
        )
        self.app = AppTest.from_string(source, default_timeout=30).run()
        self.assert_no_exception()
        return self.app

    def assert_no_exception(self):
        self.assertEqual(list(self.app.exception), [])

    def widget(self, elements, label):
        matches = [element for element in elements if element.label == label]
        self.assertEqual(len(matches), 1, f"Không tìm thấy duy nhất widget: {label}")
        return matches[0]

    def click(self, label):
        self.widget(self.app.button, label).click().run()
        self.assert_no_exception()

    def with_store(self, operation):
        store = ExpenseStore(self.db_path)
        try:
            return operation(store)
        finally:
            store.close()

    def seed(self, kind="expense", category="Ăn uống", amount=50_000, note="Cơm trưa"):
        return self.with_store(lambda store: store.add_transaction(
            self.today.isoformat(), kind, category, amount, note
        ))

    def records(self):
        return self.with_store(lambda store: store.list_transactions())

    def ledger_frame(self):
        matches = [table.value for table in self.app.dataframe if "Mã GD" in table.value.columns]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_empty_dashboard_and_quick_add_rejects_zero(self):
        app = self.open_app()
        self.assertEqual([tab.label for tab in app.tabs], [
            "📊 Tổng quan", "📈 Biểu đồ theo tháng", "🚨 Cảnh báo & Ngân sách", "📝 Sổ giao dịch"
        ])
        self.assertEqual(self.records(), [])

        app.number_input(key="quick_amount_expense").set_value(0)
        self.click("💾 Lưu giao dịch")
        self.assertTrue(any("Không lưu được giao dịch" in error.value for error in app.error))
        self.assertEqual(self.records(), [])

        app.number_input(key="quick_amount_expense").set_value(65_000)
        self.widget(app.sidebar.text_input, "Ghi chú chi tiết").set_value("Cơm và nước")
        self.click("💾 Lưu giao dịch")
        record, = self.records()
        self.assertEqual((record.kind, record.category, record.amount, record.note),
                         ("expense", "Ăn uống", 65_000, "Cơm và nước"))
        self.assertEqual(record.date, self.today.isoformat())
        self.assertTrue(any("Đã lưu giao dịch" in notice.value for notice in app.success))

    def test_edit_validates_amount_and_can_change_transaction_type(self):
        record_id = self.seed()
        app = self.open_app()
        self.widget(app.number_input, "Số tiền mới (VNĐ)").set_value(0)
        self.click("Lưu thay đổi")
        self.assertTrue(any("Không sửa được giao dịch" in error.value for error in app.error))
        record, = self.records()
        self.assertEqual((record.amount, record.note), (50_000, "Cơm trưa"))

        app.radio(key=f"edit_kind_{record_id}").set_value("income").run()
        self.assert_no_exception()
        self.widget(app.selectbox, "Danh mục mới").select("Làm thêm")
        self.widget(app.number_input, "Số tiền mới (VNĐ)").set_value(300_000)
        self.widget(app.text_input, "Ghi chú mới").set_value("Lương ca tối")
        self.click("Lưu thay đổi")
        record, = self.records()
        self.assertEqual((record.id, record.kind, record.category, record.amount, record.note),
                         (record_id, "income", "Làm thêm", 300_000, "Lương ca tối"))

    def test_delete_requires_explicit_confirmation(self):
        self.seed()
        app = self.open_app()
        self.click("Xóa giao dịch")
        self.assertEqual(len(self.records()), 1)
        self.assertTrue(any("Đánh dấu xác nhận" in warning.value for warning in app.warning))

        app.checkbox[0].check()
        self.click("Xóa giao dịch")
        self.assertEqual(self.records(), [])
        self.assertTrue(any("Đã xóa giao dịch" in notice.value for notice in app.success))

    def test_demo_does_not_reseed_after_deleting_last_transaction(self):
        record_id = self.seed(note="Giao dịch mẫu cuối cùng")
        app = self.open_app(demo=True)
        self.assertEqual([record.id for record in self.records()], [record_id])
        self.assertEqual(self.with_store(lambda store: store.connection.execute(
            "SELECT COUNT(*) FROM budgets"
        ).fetchone()[0]), 0)

        app.checkbox[0].check()
        self.click("Xóa giao dịch")
        self.assertEqual(self.records(), [])
        app.run()
        self.assert_no_exception()
        self.assertEqual(self.records(), [])
        self.assertEqual(self.with_store(lambda store: store.connection.execute(
            "SELECT COUNT(*) FROM budgets"
        ).fetchone()[0]), 0)

    def test_save_budget_and_zero_removes_only_selected_limits(self):
        app = self.open_app()
        total_key = f"budget_{self.month}_{TOTAL_BUDGET_CATEGORY}"
        food_key = f"budget_{self.month}_Ăn uống"
        app.number_input(key=total_key).set_value(3_000_000)
        app.number_input(key=food_key).set_value(500_000)
        self.click("💾 Lưu ngân sách")
        limits = self.with_store(lambda store: {
            status.category: status.limit for status in store.budget_statuses(self.month)
        })
        self.assertEqual(limits, {TOTAL_BUDGET_CATEGORY: 3_000_000, "Ăn uống": 500_000})

        app.number_input(key=total_key).set_value(0)
        app.number_input(key=food_key).set_value(600_000)
        self.click("💾 Lưu ngân sách")
        limits = self.with_store(lambda store: {
            status.category: status.limit for status in store.budget_statuses(self.month)
        })
        self.assertEqual(limits, {"Ăn uống": 600_000})

    def test_literal_search_and_filters_also_limit_csv_export(self):
        expected_id = self.seed(note="Giảm 10%_ ở quán O'Brien")
        self.seed(note="Giảm 100 ở quán khác")
        self.seed(kind="income", category="Làm thêm", amount=500_000, note="Hoàn 10%_")
        with patch("expense_tracker.ui._csv_bytes", wraps=_csv_bytes) as export:
            app = self.open_app()
            self.widget(app.text_input, "🔍 Tìm theo ghi chú hoặc danh mục").set_value("10%_").run()
            self.assert_no_exception()
            self.assertEqual(len(self.ledger_frame()), 2)

            self.widget(app.selectbox, "Lọc theo loại").select("Chi tiêu").run()
            self.widget(app.selectbox, "Lọc theo danh mục").select("Ăn uống").run()
            self.assert_no_exception()
            self.assertEqual(self.ledger_frame()["Mã GD"].tolist(), [expected_id])
            exported_records, = export.call_args.args
            self.assertEqual([record.id for record in exported_records], [expected_id])
            rows = list(csv.reader(io.StringIO(_csv_bytes(exported_records).decode("utf-8-sig"))))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1][0], str(expected_id))
            self.assertEqual(rows[1][-1], "Giảm 10%_ ở quán O'Brien")


if __name__ == "__main__":
    unittest.main()
