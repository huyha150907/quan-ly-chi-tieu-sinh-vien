"""Các hàm định dạng dùng chung cho giao diện, không phụ thuộc Tkinter."""

import re
from datetime import date


def money(value: int) -> str:
    return f"{value:,}".replace(",", ".") + " đ"


def compact_money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}".replace(".", ",") + " tr"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f}k"
    return str(round(value))


def parse_amount(text: str) -> int:
    """Chỉ chấp nhận số nguyên hoặc nhóm nghìn đúng chuẩn, tránh hiểu sai số lẻ."""
    text = text.strip()
    if not re.fullmatch(r"[0-9]+", text):
        if not re.fullmatch(r"[1-9][0-9]{0,2}([., ])[0-9]{3}(?:\1[0-9]{3})*", text):
            raise ValueError("Nhập số tiền nguyên, ví dụ 50000 hoặc 1.200.000.")
        text = re.sub(r"[., ]", "", text)
    amount = int(text)
    if not 0 < amount <= 1_000_000_000_000:
        raise ValueError("Số tiền phải lớn hơn 0 và không quá 1.000 tỷ đồng.")
    return amount


def validate_month(value: str) -> str:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
        raise ValueError("Nhập tháng theo mẫu YYYY-MM, ví dụ 2026-11.")
    try:
        date.fromisoformat(value + "-01")
    except ValueError:
        raise ValueError("Tháng không hợp lệ.") from None
    return value


def shift_month(value: str, offset: int) -> str:
    validate_month(value)
    year, month = map(int, value.split("-"))
    index = (year - 1) * 12 + month - 1 + offset
    if not 0 <= index < 9999 * 12:
        raise ValueError("Tháng nằm ngoài phạm vi hỗ trợ.")
    return f"{index // 12 + 1:04d}-{index % 12 + 1:02d}"


def display_date(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")
