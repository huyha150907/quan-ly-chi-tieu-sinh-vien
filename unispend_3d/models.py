# -*- coding: utf-8 -*-
"""
Module models.py
Định nghĩa các lớp dữ liệu (OOP) cho Ứng dụng Quản lý Chi tiêu Sinh viên.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


# Danh mục mặc định cho Chi tiêu và Thu nhập của sinh viên
EXPENSE_CATEGORIES: Dict[str, Dict[str, str]] = {
    "Tiền ăn": {"icon": "🍜", "color": "#FF6B6B", "desc": "Ăn sáng, cơm trưa/tối, đồ ăn vặt, trà sữa"},
    "Tiền trọ": {"icon": "🏠", "color": "#4ECDC4", "desc": "Tiền thuê phòng, điện, nước, internet, dịch vụ"},
    "Đi lại": {"icon": "🛵", "color": "#45B7D1", "desc": "Xăng xe, vé xe buýt, gửi xe, Grab/Be, sửa xe"},
    "Học tập": {"icon": "📚", "color": "#96CEB4", "desc": "Học phí, giáo trình, in ấn tài liệu, dụng cụ học tập"},
    "Sinh hoạt & Mua sắm": {"icon": "🛍️", "color": "#FECA57", "desc": "Quần áo, đồ dùng cá nhân, bột giặt, dầu gội"},
    "Giải trí & Xã giao": {"icon": "🎮", "color": "#A29BFE", "desc": "Xem phim, cà phê bạn bè, sinh nhật, CLB"},
    "Chi phí khác": {"icon": "💊", "color": "#FD79A8", "desc": "Thuốc men, y tế, phát sinh ngoài dự kiến"},
}

INCOME_CATEGORIES: Dict[str, Dict[str, str]] = {
    "Trợ cấp gia đình": {"icon": "👨‍👩‍👧", "color": "#00B894", "desc": "Bố mẹ gửi hàng tháng"},
    "Làm thêm (Part-time)": {"icon": "💼", "color": "#0984E3", "desc": "Lương gia sư, phục vụ, thực tập, freelance"},
    "Học bổng & Thưởng": {"icon": "🏆", "color": "#FDCB6E", "desc": "Học bổng trường, giải thưởng cuộc thi"},
    "Thu nhập khác": {"icon": "🎁", "color": "#6C5CE7", "desc": "Lì xì, bán đồ cũ, hoàn tiền"},
}


@dataclass
class Transaction:
    """
    Lớp đại diện cho một khoản giao dịch (Thu hoặc Chi).
    Áp dụng lập trình hướng đối tượng (OOP) theo yêu cầu học phần.
    """
    id: int
    date: str          # Định dạng YYYY-MM-DD
    tx_type: str       # 'Chi tiêu' hoặc 'Thu nhập'
    category: str      # Danh mục: Tiền ăn, Tiền trọ, Đi lại, ...
    amount: float      # Số tiền (VNĐ)
    note: str          # Ghi chú chi tiết

    def validate(self) -> tuple[bool, str]:
        """Kiểm tra tính hợp lệ của dữ liệu đầu vào."""
        if self.amount is None or self.amount <= 0:
            return False, "Số tiền phải lớn hơn 0 VNĐ!"
        if self.amount > 500_000_000:
            return False, "Số tiền quá lớn (tối đa 500.000.000 VNĐ cho một giao dịch)!"
        if self.tx_type not in ("Chi tiêu", "Thu nhập"):
            return False, "Loại giao dịch không hợp lệ (chỉ nhận 'Chi tiêu' hoặc 'Thu nhập')."
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            return False, "Ngày giao dịch không đúng định dạng YYYY-MM-DD."
        if not self.category or not self.category.strip():
            return False, "Vui lòng chọn danh mục giao dịch."
        return True, "Hợp lệ"

    @property
    def month_key(self) -> str:
        """Trả về chuỗi tháng YYYY-MM của giao dịch."""
        return self.date[:7]


@dataclass
class BudgetConfig:
    """
    Lớp lưu trữ cấu hình ngân sách định mức theo tháng của sinh viên.
    """
    month: str                     # Định dạng YYYY-MM
    total_budget: float            # Tổng ngân sách chi tiêu tối đa trong tháng
    category_limits: Dict[str, float]  # Định mức riêng cho từng hạng mục (Tiền ăn, Tiền trọ, Đi lại...)

    def check_alerts(self, spent_by_category: Dict[str, float]) -> List[Dict]:
        """
        Kiểm tra và trả về danh sách các cảnh báo vượt ngân sách hoặc sắp chạm ngưỡng.
        """
        alerts = []
        total_spent = sum(spent_by_category.values())

        # 1. Kiểm tra tổng ngân sách tháng
        if self.total_budget > 0:
            pct = (total_spent / self.total_budget) * 100
            if pct > 100:
                alerts.append({
                    "level": "danger",
                    "scope": "Tổng ngân sách tháng",
                    "spent": total_spent,
                    "limit": self.total_budget,
                    "percent": pct,
                    "diff": total_spent - self.total_budget,
                    "message": f"BÁO ĐỘNG ĐỎ: Tổng chi tiêu đã VƯỢT ngân sách tháng {(total_spent - self.total_budget):,.0f} đ ({pct:.1f}%)!"
                })
            elif pct >= 80:
                alerts.append({
                    "level": "warning",
                    "scope": "Tổng ngân sách tháng",
                    "spent": total_spent,
                    "limit": self.total_budget,
                    "percent": pct,
                    "diff": self.total_budget - total_spent,
                    "message": f"CẢNH BÁO SỚM: Bạn đã dùng {pct:.1f}% tổng ngân sách tháng. Chỉ còn {(self.total_budget - total_spent):,.0f} đ!"
                })
            else:
                alerts.append({
                    "level": "safe",
                    "scope": "Tổng ngân sách tháng",
                    "spent": total_spent,
                    "limit": self.total_budget,
                    "percent": pct,
                    "diff": self.total_budget - total_spent,
                    "message": f"AN TOÀN: Tổng chi tiêu đang ở mức {pct:.1f}% ({total_spent:,.0f} / {self.total_budget:,.0f} đ)."
                })

        # 2. Kiểm tra ngân sách từng danh mục
        for cat, limit in self.category_limits.items():
            if limit <= 0:
                continue
            spent = spent_by_category.get(cat, 0.0)
            pct = (spent / limit) * 100
            if pct > 100:
                alerts.append({
                    "level": "danger",
                    "scope": cat,
                    "spent": spent,
                    "limit": limit,
                    "percent": pct,
                    "diff": spent - limit,
                    "message": f"Vượt định mức [{cat}]: Đã chi {spent:,.0f} đ / Định mức {limit:,.0f} đ (Vượt {(spent - limit):,.0f} đ - {pct:.1f}%)"
                })
            elif pct >= 80:
                alerts.append({
                    "level": "warning",
                    "scope": cat,
                    "spent": spent,
                    "limit": limit,
                    "percent": pct,
                    "diff": limit - spent,
                    "message": f"Sắp hết định mức [{cat}]: Đã chi {spent:,.0f} đ / {limit:,.0f} đ ({pct:.1f}% - Còn {(limit - spent):,.0f} đ)"
                })

        return alerts
