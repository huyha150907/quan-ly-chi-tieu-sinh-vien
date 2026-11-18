# -*- coding: utf-8 -*-
"""
Module backend.py (Tầng Xử Lý Nghiệp Vụ - Backend Controller)
-------------------------------------------------------------------------
File này đóng vai trò cầu nối giữa Giao diện (app.py) và Cơ sở dữ liệu (database.py)
trong IDE. Tất cả các tính toán thống kê Tiền ăn, Tiền trọ, Đi lại, kiểm tra
vượt ngân sách, và chuẩn bị dữ liệu biểu đồ đều được xử lý tại đây.
"""

from typing import Dict, List, Any, Tuple
import pandas as pd

if __package__:
    from .models import Transaction, BudgetConfig, EXPENSE_CATEGORIES, INCOME_CATEGORIES
    from .database import ExpenseDatabase
else:
    from models import Transaction, BudgetConfig, EXPENSE_CATEGORIES, INCOME_CATEGORIES
    from database import ExpenseDatabase


class ExpenseBackend:
    """
    Lớp Backend chính cung cấp API nội bộ cho file giao diện (app.py) gọi tới.
    """

    def __init__(self, db_path: str = "data/student_expense.db"):
        self.db = ExpenseDatabase(db_path)

    # =========================================================================
    # 1. API QUẢN LÝ GIAO DỊCH THU / CHI HẰNG NGÀY
    # =========================================================================
    def get_categories(self, tx_type: str) -> Dict[str, Dict[str, str]]:
        """Trả về danh sách danh mục tương ứng với 'Chi tiêu' hoặc 'Thu nhập'."""
        if tx_type == "Chi tiêu":
            return EXPENSE_CATEGORIES
        return INCOME_CATEGORIES

    def add_daily_transaction(
        self,
        date_str: str,
        tx_type: str,
        category: str,
        amount: float,
        note: str
    ) -> Tuple[bool, str]:
        """Nhận dữ liệu từ form giao diện, kiểm tra hợp lệ và lưu vào CSDL."""
        tx, message = self.create_transaction(date_str, tx_type, category, amount, note)
        return tx is not None, message

    def create_transaction(
        self, date_str: str, tx_type: str, category: str, amount: float, note: str
    ) -> tuple[Transaction | None, str]:
        clean_note = note.strip() if note and note.strip() else f"{category} ({date_str})"
        tx = Transaction(
            id=0,
            date=date_str,
            tx_type=tx_type,
            category=category,
            amount=float(amount),
            note=clean_note
        )
        tx_id, message = self.db.insert_transaction(tx)
        if tx_id is None:
            return None, message
        tx.id = tx_id
        return tx, message

    def remove_transaction(self, tx_id: int) -> bool:
        """Xóa một giao dịch theo ID."""
        return self.db.delete_transaction(int(tx_id))

    def reset_demo_data(self) -> None:
        """Khôi phục lại dữ liệu mẫu 4 tháng cho sinh viên thuyết trình/chạy thử."""
        self.db.reset_to_sample_data()

    def get_available_months(self) -> List[str]:
        """Lấy danh sách các tháng có dữ liệu (YYYY-MM)."""
        return self.db.get_available_months()

    # =========================================================================
    # 2. API THỐNG KÊ TIỀN ĂN, TIỀN TRỌ, ĐI LẠI & CẢNH BÁO NGÂN SÁCH
    # =========================================================================
    def get_monthly_dashboard_data(self, month: str) -> Dict[str, Any]:
        """
        Tính toán toàn bộ chỉ số của một tháng để trả về cho Giao diện hiển thị:
        - Tổng thu, Tổng chi, Số dư, Ngân sách còn lại
        - Thống kê chi tiết 3 mục thiết yếu: Tiền ăn, Tiền trọ, Đi lại
        - Danh sách cảnh báo vượt ngân sách (Đỏ >= 100%, Vàng >= 80%, Xanh < 80%)
        - Bảng tổng hợp toàn bộ danh mục trong tháng
        """
        df_month = self.db.get_transactions_df(month=month)
        budget_cfg = self.db.get_budget_config(month)

        if not df_month.empty:
            total_income = float(df_month[df_month["tx_type"] == "Thu nhập"]["amount"].sum())
            df_exp = df_month[df_month["tx_type"] == "Chi tiêu"]
            total_expense = float(df_exp["amount"].sum())
            spent_by_cat = df_exp.groupby("category")["amount"].sum().to_dict()
        else:
            total_income = 0.0
            total_expense = 0.0
            df_exp = pd.DataFrame(columns=df_month.columns)
            spent_by_cat = {}

        balance = total_income - total_expense
        budget_used_pct = (total_expense / budget_cfg.total_budget * 100) if budget_cfg.total_budget > 0 else 0.0
        budget_remaining = budget_cfg.total_budget - total_expense

        # Kiểm tra cảnh báo vượt ngân sách
        alerts = budget_cfg.check_alerts(spent_by_cat)

        # Thống kê chuyên biệt 3 khoản: Tiền ăn, Tiền trọ, Đi lại
        core_3_meta = [
            ("Tiền ăn", "🍜", "#EF4444", "Ăn sáng, cơm trưa/tối, đi chợ nấu ăn, trà sữa"),
            ("Tiền trọ", "🏠", "#0D9488", "Tiền thuê nhà, điện, nước, wifi, dịch vụ"),
            ("Đi lại", "🛵", "#2563EB", "Xăng xe, gửi xe trường, xe buýt, Grab/Be"),
        ]
        essential_stats = []
        for cat_name, icon, color, desc in core_3_meta:
            spent = float(spent_by_cat.get(cat_name, 0.0))
            limit = float(budget_cfg.category_limits.get(cat_name, 1000000.0))
            pct = (spent / limit * 100) if limit > 0 else 0.0
            share = (spent / total_expense * 100) if total_expense > 0 else 0.0

            if pct > 100:
                status = "danger"
                badge_text = f"🚨 Vượt {pct - 100:.1f}%"
                note_text = f"Vượt định mức {(spent - limit):,.0f} đ!"
            elif pct >= 80:
                status = "warning"
                badge_text = f"⚠️ Đã dùng {pct:.1f}%"
                note_text = f"Sắp chạm ngưỡng! Còn {(limit - spent):,.0f} đ"
            else:
                status = "safe"
                badge_text = f"✅ An toàn ({pct:.1f}%)"
                note_text = f"Còn dư {(limit - spent):,.0f} đ trong định mức"

            essential_stats.append({
                "category": cat_name,
                "icon": icon,
                "color": color,
                "desc": desc,
                "spent": spent,
                "limit": limit,
                "percent": pct,
                "share_of_total": share,
                "status": status,
                "badge_text": badge_text,
                "note_text": note_text,
            })

        # Bảng phân tích tất cả danh mục chi tiêu
        category_table_rows = []
        for cat, meta in EXPENSE_CATEGORIES.items():
            s_val = float(spent_by_cat.get(cat, 0.0))
            l_val = float(budget_cfg.category_limits.get(cat, 0.0))
            p_val = (s_val / l_val * 100) if l_val > 0 else 0.0
            share_val = (s_val / total_expense * 100) if total_expense > 0 else 0.0
            if p_val > 100:
                state_str = "🚨 Vượt ngân sách"
            elif p_val >= 80:
                state_str = "⚠️ Sắp hết định mức"
            else:
                state_str = "✅ Trong định mức"

            category_table_rows.append({
                "Danh mục": f"{meta['icon']} {cat}",
                "Đã chi (VNĐ)": s_val,
                "Định mức (VNĐ)": l_val,
                "Tỷ lệ dùng (%)": round(p_val, 1),
                "Tỷ trọng (%)": round(share_val, 1),
                "Trạng thái": state_str
            })

        return {
            "month": month,
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": balance,
            "total_budget": budget_cfg.total_budget,
            "budget_used_pct": budget_used_pct,
            "budget_remaining": budget_remaining,
            "budget_config": budget_cfg,
            "spent_by_cat": spent_by_cat,
            "alerts": alerts,
            "essential_stats": essential_stats,
            "df_category_summary": pd.DataFrame(category_table_rows),
            "df_month": df_month,
            "df_exp_month": df_exp,
        }

    # =========================================================================
    # 3. API DỮ LIỆU BIỂU ĐỒ THEO THÁNG & THEO NGÀY
    # =========================================================================
    def get_charts_data(self, selected_month: str) -> Dict[str, pd.DataFrame]:
        """Chuẩn bị các DataFrame đã tổng hợp sẵn cho Giao diện vẽ biểu đồ."""
        df_all = self.db.get_transactions_df()
        df_month = self.db.get_transactions_df(month=selected_month)
        df_exp_month = df_month[df_month["tx_type"] == "Chi tiêu"] if not df_month.empty else pd.DataFrame()

        # 1. Biểu đồ tròn cơ cấu tháng đang chọn
        if not df_exp_month.empty:
            df_pie = (
                df_exp_month.groupby("category", as_index=False)["amount"]
                .sum()
                .sort_values("amount", ascending=False)
            )
            df_pie["pct"] = (df_pie["amount"] / df_pie["amount"].sum() * 100).round(1)
        else:
            df_pie = pd.DataFrame(columns=["category", "amount", "pct"])

        # 2. Biểu đồ Thu nhập vs Chi tiêu theo các tháng
        if not df_all.empty:
            df_monthly_io = df_all.groupby(["month", "tx_type"], as_index=False)["amount"].sum()
            df_exp_all = df_all[df_all["tx_type"] == "Chi tiêu"]
            df_monthly_cat = df_exp_all.groupby(["month", "category"], as_index=False)["amount"].sum()
            df_core3_trend = (
                df_exp_all[df_exp_all["category"].isin(["Tiền ăn", "Tiền trọ", "Đi lại"])]
                .groupby(["month", "category"], as_index=False)["amount"]
                .sum()
            )
        else:
            df_monthly_io = pd.DataFrame(columns=["month", "tx_type", "amount"])
            df_monthly_cat = pd.DataFrame(columns=["month", "category", "amount"])
            df_core3_trend = pd.DataFrame(columns=["month", "category", "amount"])

        # 3. Biểu đồ chi tiêu theo từng ngày trong tháng
        if not df_exp_month.empty:
            df_daily = df_exp_month.groupby("date", as_index=False)["amount"].sum().sort_values("date")
        else:
            df_daily = pd.DataFrame(columns=["date", "amount"])

        return {
            "pie_month": df_pie,
            "monthly_io": df_monthly_io,
            "monthly_cat": df_monthly_cat,
            "core3_trend": df_core3_trend,
            "daily_expense": df_daily,
        }

    # =========================================================================
    # 4. API CẬP NHẬT ĐỊNH MỨC NGÂN SÁCH
    # =========================================================================
    def update_budget(self, month: str, total_budget: float, category_limits: Dict[str, float]) -> None:
        """Lưu định mức ngân sách mới cho tháng."""
        cfg = BudgetConfig(
            month=month,
            total_budget=float(total_budget),
            category_limits=category_limits
        )
        self.db.save_budget_config(cfg)
