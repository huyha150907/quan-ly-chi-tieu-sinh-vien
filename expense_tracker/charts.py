"""Biểu đồ Altair và dữ liệu tổng hợp cho giao diện UniSpend."""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Iterable

import altair as alt

from .storage import BudgetStatus, EXPENSE_CATEGORIES, Transaction
from .utils import validate_month

PURPLE = "#4F46E5"
GREEN = "#10B981"
RED = "#EF4444"
CATEGORY_COLORS = (RED, "#0D9488", "#2563EB", "#8B5CF6", "#F59E0B", "#94A3B8")
ESSENTIAL_CATEGORIES = ("Ăn uống", "Tiền trọ", "Đi lại")


def _finish(chart: alt.Chart, title: str, height: int = 310) -> alt.Chart:
    return (
        chart.properties(height=height, title=title)
        .configure(background="white", font="Segoe UI")
        .configure_view(stroke=None)
        .configure_axis(
            labelColor="#64748B", titleColor="#64748B", gridColor="#EEF2F6",
            domain=False, tickColor="#E2E8F0", titleFontWeight=500,
        )
        .configure_legend(title=None, labelColor="#475569", orient="bottom")
        .configure_title(anchor="start", color="#1E293B", fontSize=15, offset=20)
    )


def _category_scale() -> alt.Scale:
    return alt.Scale(domain=list(EXPENSE_CATEGORIES), range=list(CATEGORY_COLORS))


def _monthly_category_rows(
    records: Iterable[Transaction], months: list[str],
    categories: tuple[str, ...] = EXPENSE_CATEGORIES,
) -> list[dict]:
    """Chỉ cộng khoản chi trong khoảng đã chọn, giữ cả tháng có tổng bằng 0."""
    totals = {(month, category): 0 for month in months for category in categories}
    for record in records:
        key = (record.date[:7], record.category)
        if record.kind == "expense" and key in totals:
            totals[key] += record.amount
    return [
        {"month": month, "category": category, "amount": totals[month, category]}
        for month in months for category in categories
    ]


def _daily_expense_rows(records: Iterable[Transaction], month: str) -> list[dict]:
    """Giữ mọi ngày trong tháng, bao gồm ngày không phát sinh khoản chi."""
    validate_month(month)
    year, month_number = map(int, month.split("-"))
    totals = {
        f"{month}-{day:02d}": 0
        for day in range(1, monthrange(year, month_number)[1] + 1)
    }
    for record in records:
        if record.kind == "expense" and record.date in totals:
            totals[record.date] += record.amount
    return [{"date": day, "amount": amount} for day, amount in totals.items()]


def category_donut(totals: dict[str, int]) -> alt.Chart:
    total = sum(totals.values())
    rows = [
        {"category": category, "amount": amount, "share": amount / total}
        for category, amount in totals.items() if amount > 0 and total > 0
    ]
    chart = alt.Chart(alt.Data(values=rows)).mark_arc(
        innerRadius=70, outerRadius=115, cornerRadius=6, padAngle=0.025,
    ).encode(
        theta=alt.Theta("amount:Q", title="Số tiền"),
        color=alt.Color("category:N", scale=_category_scale()),
        tooltip=[
            alt.Tooltip("category:N", title="Danh mục"),
            alt.Tooltip("amount:Q", title="Số tiền (VNĐ)", format=",.0f"),
            alt.Tooltip("share:Q", title="Tỷ trọng", format=".1%"),
        ],
    )
    return _finish(chart, "Cơ cấu chi tiêu trong tháng")


def monthly_income_expense(rows: list[dict]) -> alt.Chart:
    values = [
        {"month": row["month"], "kind": label, "amount": row[key]}
        for row in rows for key, label in (("income", "Thu nhập"), ("expense", "Chi tiêu"))
    ]
    chart = alt.Chart(alt.Data(values=values)).mark_bar(
        cornerRadiusTopLeft=5, cornerRadiusTopRight=5,
    ).encode(
        x=alt.X("month:N", title="Tháng", sort=[row["month"] for row in rows],
                axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("kind:N", sort=["Thu nhập", "Chi tiêu"]),
        y=alt.Y("amount:Q", title="Số tiền (VNĐ)"),
        color=alt.Color("kind:N", scale=alt.Scale(
            domain=["Thu nhập", "Chi tiêu"], range=[GREEN, RED],
        )),
        tooltip=[
            alt.Tooltip("month:N", title="Tháng"),
            alt.Tooltip("kind:N", title="Loại giao dịch"),
            alt.Tooltip("amount:Q", title="Số tiền (VNĐ)", format=",.0f"),
        ],
    )
    return _finish(chart, "So sánh thu nhập và chi tiêu")


def monthly_categories(records: Iterable[Transaction], months: list[str]) -> alt.Chart:
    chart = alt.Chart(alt.Data(values=_monthly_category_rows(records, months))).mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
    ).encode(
        x=alt.X("month:N", title="Tháng", sort=months, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("amount:Q", title="Chi tiêu (VNĐ)"),
        color=alt.Color("category:N", scale=_category_scale()),
        tooltip=[
            alt.Tooltip("month:N", title="Tháng"),
            alt.Tooltip("category:N", title="Danh mục"),
            alt.Tooltip("amount:Q", title="Chi tiêu (VNĐ)", format=",.0f"),
        ],
    )
    return _finish(chart, "Chi tiêu theo tháng và danh mục")


def essential_trend(records: Iterable[Transaction], months: list[str]) -> alt.Chart:
    rows = _monthly_category_rows(records, months, ESSENTIAL_CATEGORIES)
    chart = alt.Chart(alt.Data(values=rows)).mark_line(
        strokeWidth=3, point=alt.OverlayMarkDef(size=70, filled=True),
    ).encode(
        x=alt.X("month:N", title="Tháng", sort=months, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("amount:Q", title="Số tiền (VNĐ)"),
        color=alt.Color("category:N", scale=alt.Scale(
            domain=list(ESSENTIAL_CATEGORIES), range=list(CATEGORY_COLORS[:3]),
        )),
        tooltip=[
            alt.Tooltip("month:N", title="Tháng"),
            alt.Tooltip("category:N", title="Khoản thiết yếu"),
            alt.Tooltip("amount:Q", title="Số tiền (VNĐ)", format=",.0f"),
        ],
    )
    return _finish(chart, "Biến động tiền ăn, tiền trọ và đi lại", 280)


def daily_expenses(records: Iterable[Transaction], month: str) -> alt.Chart:
    chart = alt.Chart(alt.Data(values=_daily_expense_rows(records, month))).mark_area(
        line={"color": PURPLE, "strokeWidth": 2.5},
        color=alt.Gradient(
            gradient="linear", x1=1, x2=1, y1=1, y2=0,
            stops=[alt.GradientStop(color="#EEF2FF", offset=0),
                   alt.GradientStop(color="#818CF8", offset=1)],
        ),
        point=alt.OverlayMarkDef(color=PURPLE, size=35),
    ).encode(
        x=alt.X("date:O", title="Ngày trong tháng", axis=alt.Axis(
            labelAngle=0, labelExpr="substring(datum.label, 8, 10)",
        )),
        y=alt.Y("amount:Q", title="Chi tiêu (VNĐ)"),
        tooltip=[
            alt.Tooltip("date:N", title="Ngày"),
            alt.Tooltip("amount:Q", title="Tổng chi (VNĐ)", format=",.0f"),
        ],
    )
    return _finish(chart, f"Chi tiêu hằng ngày · {month}", 270)


def budget_comparison(statuses: Iterable[BudgetStatus]) -> alt.Chart:
    statuses = list(statuses)
    rows = [
        {"category": status.category, "kind": label, "amount": amount}
        for status in statuses
        for label, amount in (("Đã chi thực tế", status.spent), ("Định mức", status.limit))
    ]
    chart = alt.Chart(alt.Data(values=rows)).mark_bar(cornerRadiusEnd=5).encode(
        y=alt.Y("category:N", title=None, sort=[status.category for status in statuses]),
        yOffset=alt.YOffset("kind:N", sort=["Đã chi thực tế", "Định mức"]),
        x=alt.X("amount:Q", title="Số tiền (VNĐ)"),
        color=alt.Color("kind:N", scale=alt.Scale(
            domain=["Đã chi thực tế", "Định mức"], range=[RED, "#94A3B8"],
        )),
        tooltip=[
            alt.Tooltip("category:N", title="Danh mục"),
            alt.Tooltip("kind:N", title="Loại"),
            alt.Tooltip("amount:Q", title="Số tiền (VNĐ)", format=",.0f"),
        ],
    )
    return _finish(chart, "Chi tiêu thực tế và định mức ngân sách", max(240, len(statuses) * 55))
