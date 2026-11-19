"""Kiểm thử giao diện UTH bằng cơ sở dữ liệu tạm."""

import gc
import importlib
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest


APP_DIRECTORY = Path(__file__).resolve().parents[1] / "unispend_3d"


class UniSpend3dInputTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(gc.collect)
        self.path_patch = patch.object(sys, "path", [str(APP_DIRECTORY), *sys.path])
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        backend_module = importlib.import_module("backend")
        self.backend = backend_module.ExpenseBackend(str(Path(self.directory.name) / "ui_3d.db"))
        self.backend_patch = patch.object(backend_module, "ExpenseBackend", lambda _path: self.backend)
        self.backend_patch.start()
        self.addCleanup(self.backend_patch.stop)
        st.cache_resource.clear()
        self.addCleanup(st.cache_resource.clear)
        self.app = AppTest.from_file(str(APP_DIRECTORY / "app.py"), default_timeout=30).run()
        self.assert_no_exception()

    def assert_no_exception(self):
        self.assertEqual(list(self.app.exception), [])

    def save(self):
        self.click("Nhập khoản giao dịch")

    def click(self, label):
        next(button for button in self.app.button if button.label == label).click().run()
        self.assert_no_exception()

    def saved_record(self, note):
        records = self.backend.db.get_transactions_df()
        matches = records[records["note"] == note]
        self.assertEqual(len(matches), 1)
        return matches.iloc[0]

    def ledger_frame(self):
        frames = [table.value for table in self.app.dataframe if "note" in table.value.columns]
        self.assertEqual(len(frames), 1)
        return frames[0]

    def test_direct_save_commits_current_fields_and_opens_saved_month(self):
        self.app.date_input(key="tx_date").set_value(date(2025, 12, 31))
        self.app.selectbox(key="tx_category").select("Đi lại")
        self.app.number_input(key="tx_amount").set_value(76_543)
        self.app.text_input(key="tx_note").set_value("Vé xe nhập trực tiếp")
        self.save()

        record = self.saved_record("Vé xe nhập trực tiếp")
        self.assertEqual((record["date"], record["category"], record["amount"], record["tx_type"]),
                         ("2025-12-31", "Đi lại", 76_543, "Chi tiêu"))
        self.assertEqual(self.app.selectbox(key="report_month").value, "2025-12")
        self.assertEqual(self.ledger_frame()["id"].tolist(), [record["id"]])
        self.assertTrue(any("thành công" in notice.value for notice in self.app.success))

    def test_original_tabs_and_wallet_image_are_available(self):
        self.assertEqual([tab.label for tab in self.app.tabs],
                         ["Tổng quan", "Thu chi", "Biểu đồ & Ngân sách", "Việc cần làm"])
        self.assertTrue(any("data:image/jpeg;base64," in str(element.proto) for element in self.app.get("html")))

    def test_selecting_income_uses_income_category(self):
        self.app.radio[0].set_value("Thu nhập").run()
        self.assert_no_exception()
        self.app.selectbox(key="tx_category").select("Làm thêm (Part-time)")
        self.app.text_input(key="tx_note").set_value("Lương ca tối")
        self.app.number_input(key="tx_amount").set_value(180_001)
        self.save()
        record = self.saved_record("Lương ca tối")
        self.assertEqual((record["tx_type"], record["category"], record["amount"]),
                         ("Thu nhập", "Làm thêm (Part-time)", 180_001))

    def test_invalid_zero_keeps_draft_without_writing(self):
        count = len(self.backend.db.get_transactions_df())
        self.app.number_input(key="tx_amount").set_value(0)
        self.app.text_input(key="tx_note").set_value("Giữ ghi chú khi nhập sai")
        self.save()
        self.assertEqual(len(self.backend.db.get_transactions_df()), count)
        self.assertTrue(any("lớn hơn 0" in error.value for error in self.app.error))
        self.assertEqual(self.app.text_input(key="tx_note").value, "Giữ ghi chú khi nhập sai")
        self.app.number_input(key="tx_amount").set_value(65_555)
        self.save()
        self.assertEqual(self.saved_record("Giữ ghi chú khi nhập sai")["amount"], 65_555)

    def test_search_treats_regex_characters_as_literal_text(self):
        month = self.app.selectbox(key="report_month").value
        for note in ("Quán [cơm] giảm 10%_", "Mua vật dụng .*", "Cơm bình thường"):
            ok, message = self.backend.add_daily_transaction(month + "-01", "Chi tiêu", "Tiền ăn", 10_000, note)
            self.assertTrue(ok, message)
        for keyword, expected_note in (("[cơm]", "Quán [cơm] giảm 10%_"),
                                       (".*", "Mua vật dụng .*"),
                                       ("10%_", "Quán [cơm] giảm 10%_")):
            with self.subTest(keyword=keyword):
                self.app.text_input(key="ledger_search").set_value(keyword).run()
                self.assert_no_exception()
                self.assertEqual(self.ledger_frame()["note"].tolist(), [expected_note])

    def test_budget_changes_apply_to_selected_month(self):
        picker = self.app.selectbox(key="report_month")
        month, other_month = picker.options[:2]
        other_budget = self.backend.db.get_budget_config(other_month)
        self.app.number_input(key=f"budget_total_{month}").set_value(6_000_000)
        self.app.number_input(key=f"canva_lim_{month}_Tiền ăn").set_value(1_800_000)
        self.click("Lưu định mức ngân sách")
        budget = self.backend.db.get_budget_config(month)
        self.assertEqual((budget.total_budget, budget.category_limits["Tiền ăn"]), (6_000_000, 1_800_000))
        self.assertEqual(self.backend.db.get_budget_config(other_month), other_budget)

    def test_csv_import_preserves_amounts_and_skips_report_totals(self):
        csv = (
            "Ngày giao dịch,Loại giao dịch,Danh mục,Số tiền (VNĐ),Ghi chú chi tiết\n"
            "15/01/2024,Chi tiêu,Tiền ăn,35000.0,Cơm CSV\n"
            "16/01/2024,Thu nhập,Trợ cấp gia đình,150.000,Thu CSV\n"
            ",TỔNG CHI,,35000,\n"
        )
        self.app.file_uploader(key="import_csv_uploader_0").upload(
            "giao-dich.csv", csv.encode("utf-8-sig"), "text/csv"
        ).run()
        self.click("✅ Xác nhận nhập vào sổ")
        self.assertEqual(self.saved_record("Cơm CSV")["amount"], 35_000)
        self.assertEqual(self.saved_record("Thu CSV")["amount"], 150_000)
        self.assertEqual(len(self.ledger_frame()), 2)
        self.assertEqual(self.app.selectbox(key="report_month").value, "2024-01")

    def test_invalid_csv_row_keeps_entire_batch_out_of_database(self):
        csv = (
            "date,tx_type,category,amount\n"
            "2024-01-15,Chi tiêu,Tiền ăn,35000\n"
            "2024-01-16,Chi tiêu,Tiền ăn,không rõ\n"
        )
        count = len(self.backend.db.get_transactions_df())
        self.app.file_uploader(key="import_csv_uploader_0").upload(
            "giao-dich.csv", csv.encode(), "text/csv"
        ).run()
        self.assert_no_exception()
        self.assertTrue(any("Dòng 3" in error.value for error in self.app.error))
        self.assertFalse(any("Xác nhận nhập" in button.label for button in self.app.button))
        self.assertEqual(len(self.backend.db.get_transactions_df()), count)


if __name__ == "__main__":
    unittest.main()
