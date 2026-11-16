"""Kiểm thử nhập liệu UniSpend 3D bằng cơ sở dữ liệu tạm."""

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
        buttons = [button for button in self.app.sidebar.button if button.label == "💾 Lưu Giao Dịch Ngay"]
        self.assertEqual(len(buttons), 1)
        buttons[0].click().run()
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
        self.app.date_input(key="quick_date").set_value(date(2025, 12, 31))
        self.app.selectbox(key="quick_category_expense").select("Đi lại")
        self.app.number_input(key="quick_amount").set_value(76_543)
        self.app.text_input(key="quick_note").set_value("Vé xe nhập trực tiếp")
        self.save()

        record = self.saved_record("Vé xe nhập trực tiếp")
        self.assertEqual((record["date"], record["category"], record["amount"], record["tx_type"]),
                         ("2025-12-31", "Đi lại", 76_543, "Chi tiêu"))
        self.assertEqual(self.app.selectbox(key="report_month").value, "2025-12")
        self.assertEqual(self.ledger_frame()["id"].tolist(), [record["id"]])
        self.assertTrue(any("thành công" in notice.value for notice in self.app.success))

    def test_quick_amount_buttons_preserve_draft_and_save_selected_amount(self):
        for amount in (35_000, 50_000, 200_000):
            with self.subTest(amount=amount):
                note = f"Khoản chọn nhanh {amount}"
                self.app.selectbox(key="quick_category_expense").select("Tiền trọ")
                self.app.number_input(key="quick_amount").set_value(99_999)
                self.app.text_input(key="quick_note").set_value(note)
                self.app.button(key=f"quick_{amount}").click().run()
                self.assert_no_exception()
                self.assertEqual(self.app.text_input(key="quick_note").value, note)
                self.assertEqual(self.app.selectbox(key="quick_category_expense").value, "Tiền trọ")
                self.assertEqual(self.app.number_input(key="quick_amount").value, amount)
                self.save()
                record = self.saved_record(note)
                self.assertEqual((record["amount"], record["category"]), (amount, "Tiền trọ"))

    def test_changing_to_income_uses_income_category_and_preserves_typed_note(self):
        self.app.selectbox(key="quick_category_expense").select("Đi lại")
        self.app.text_input(key="quick_note").set_value("Lương ca tối")
        self.app.radio(key="sidebar_tx_type").set_value("Thu nhập").run()
        self.assert_no_exception()
        self.assertEqual(self.app.text_input(key="quick_note").value, "Lương ca tối")
        self.app.selectbox(key="quick_category_income").select("Làm thêm (Part-time)")
        self.app.number_input(key="quick_amount").set_value(180_001)
        self.save()
        record = self.saved_record("Lương ca tối")
        self.assertEqual((record["tx_type"], record["category"], record["amount"]),
                         ("Thu nhập", "Làm thêm (Part-time)", 180_001))

    def test_invalid_zero_keeps_draft_without_writing(self):
        count = len(self.backend.db.get_transactions_df())
        self.app.number_input(key="quick_amount").set_value(0)
        self.app.text_input(key="quick_note").set_value("Giữ ghi chú khi nhập sai")
        self.save()
        self.assertEqual(len(self.backend.db.get_transactions_df()), count)
        self.assertTrue(any("lớn hơn 0" in error.value for error in self.app.error))
        self.assertEqual(self.app.text_input(key="quick_note").value, "Giữ ghi chú khi nhập sai")
        self.app.number_input(key="quick_amount").set_value(65_555)
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

    def test_simulator_uses_actual_expenses_below_and_above_original_ranges(self):
        expected = [0, 0, 0]
        for index, (category, amount) in enumerate((("Tiền ăn", 45_000),
                                                     ("Tiền trọ", 6_000_000),
                                                     ("Đi lại", 3_000_000))):
            with self.subTest(category=category):
                self.app.date_input(key="quick_date").set_value(date(2020, 1, 15))
                self.app.selectbox(key="quick_category_expense").select(category)
                self.app.number_input(key="quick_amount").set_value(amount)
                self.app.text_input(key="quick_note").set_value(f"Kiểm tra giả lập {category}")
                self.save()
                expected[index] = amount
                self.assertEqual(self.app.selectbox(key="report_month").value, "2020-01")
                self.assertEqual([slider.value for slider in self.app.slider], expected)


if __name__ == "__main__":
    unittest.main()
