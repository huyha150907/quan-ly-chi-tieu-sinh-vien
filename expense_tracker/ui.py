"""Giao diện web UniSpend, sử dụng dữ liệu SQLite hiện có của ứng dụng."""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from . import charts
from .storage import (
    EXPENSE_CATEGORIES, INCOME_CATEGORIES, MAX_AMOUNT,
    TOTAL_BUDGET_CATEGORY, TYPE_LABELS, ExpenseStore,
)
from .utils import money, validate_month


CATEGORY_META = {
    "Ăn uống": ("🍜", "Tiền ăn", "#EF4444", "Ăn uống hằng ngày, thực phẩm và đồ uống"),
    "Tiền trọ": ("🏠", "Tiền trọ", "#0D9488", "Tiền phòng, điện nước và sinh hoạt"),
    "Đi lại": ("🛵", "Đi lại", "#2563EB", "Xăng xe, vé xe buýt và di chuyển"),
    "Học tập": ("📚", "Học tập", "#8B5CF6", ""),
    "Giải trí": ("🎮", "Giải trí", "#F59E0B", ""),
    "Khác": ("📦", "Khác", "#64748B", ""),
}


def _category_label(category):
    icon, title, *_ = CATEGORY_META.get(category, ("💰", category))
    return f"{icon} {title}"


def _notice(message):
    st.session_state["notice"] = message
    st.rerun()


def _status_text(status):
    if status.exceeded:
        return "danger", "Vượt ngân sách", f"Vượt định mức {money(-status.remaining)}"
    if status.near_limit:
        return "warning", "Sắp chạm ngưỡng", f"Đã dùng {status.ratio:.1%} định mức"
    return "safe", "Trong định mức", f"Còn có thể chi {money(status.remaining)}"


def _sidebar(store, demo):
    with st.sidebar:
        st.markdown('''<div class="brand"><div class="brand-icon">🎓💳</div>
            <div class="brand-name">UniSpend</div>
            <div class="muted">Quản lý chi tiêu sinh viên</div></div>''', unsafe_allow_html=True)
        today = date.today()
        if st.session_state.pop("reset_quick_form", False):
            st.session_state["quick_date"] = today
            st.session_state["quick_amount"] = 45_000
            st.session_state["quick_note"] = ""
        pending = st.session_state.pop("pending_month", None)
        if pending:
            st.session_state["report_month"] = pending
        selected = st.session_state.get("report_month", today.strftime("%Y-%m"))
        months = sorted(set(store.available_months() + [today.strftime("%Y-%m"), selected]), reverse=True)
        month = st.selectbox("📅 Chọn tháng xem báo cáo", months, key="report_month")
        with st.expander("Xem một tháng khác"):
            with st.form("choose_month", enter_to_submit=False):
                custom_month = st.text_input("Tháng (YYYY-MM)", value=month)
                if st.form_submit_button("Xem tháng", width="stretch"):
                    try:
                        st.session_state["pending_month"] = validate_month(custom_month.strip())
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        st.divider()
        st.markdown("### ➕ Nhập khoản thu / chi")
        kind_label = st.radio("Loại giao dịch", ["Chi tiêu", "Thu nhập"], horizontal=True, key="quick_kind")
        kind = "expense" if kind_label == "Chi tiêu" else "income"
        categories = EXPENSE_CATEGORIES if kind == "expense" else INCOME_CATEGORIES
        st.session_state.setdefault("quick_amount", 45_000)
        with st.container(border=True):
            category = st.selectbox("Danh mục", categories, format_func=_category_label, key=f"quick_category_{kind}")
            transaction_date = st.date_input("Ngày giao dịch", min_value=date.min, max_value=date.max,
                                             key="quick_date")
            amount = st.number_input("Số tiền (VNĐ)", min_value=0, max_value=MAX_AMOUNT,
                                     step=5_000, format="%d", key="quick_amount")
            note = st.text_input("Ghi chú chi tiết", max_chars=200, placeholder="VD: Cơm trưa, đổ xăng, tiền trọ…",
                                 key="quick_note")
            if st.button("💾 Lưu giao dịch", type="primary", width="stretch"):
                try:
                    store.add_transaction(transaction_date.isoformat(), kind, category, amount, note)
                except (ValueError, sqlite3.Error) as exc:
                    st.error(f"Không lưu được giao dịch: {exc}")
                else:
                    st.session_state["pending_month"] = transaction_date.strftime("%Y-%m")
                    st.session_state["reset_quick_form"] = True
                    _notice("Đã lưu giao dịch thành công.")
        st.divider()
        if demo:
            st.info("Bạn đang sử dụng dữ liệu mẫu, được lưu riêng với dữ liệu cá nhân.")
        else:
            st.caption("🔒 Dữ liệu được lưu trên máy của bạn.")
        st.caption("Đơn vị: đồng Việt Nam (VNĐ)")
    return month


def _hero(month, demo):
    year, number = month.split("-")
    st.markdown(f'''<div class="hero-banner"><div>
        <div class="hero-title">🎓 UniSpend — Quản Lý Chi Tiêu Sinh Viên</div>
        <p class="hero-subtitle">Nhập thu chi hằng ngày • Theo dõi khoản chi thiết yếu • Chủ động ngân sách</p>
        </div><div class="hero-badge"><span>KỲ BÁO CÁO{' · DỮ LIỆU MẪU' if demo else ''}</span>
        <strong>Tháng {number} / {year}</strong></div></div>''', unsafe_allow_html=True)


def _alerts(statuses, *, detailed=False):
    active = [status for status in statuses if status.near_limit]
    if detailed:
        active = statuses
    if not statuses:
        st.info("Chưa đặt ngân sách tháng này. Mở tab Cảnh báo & Ngân sách để thiết lập hạn mức.")
    elif not active:
        st.markdown('<div class="alert-box alert-safe">✅ <strong>Chi tiêu đang trong định mức ngân sách đã đặt.</strong></div>', unsafe_allow_html=True)
    for status in active:
        level, title, detail = _status_text(status)
        st.markdown(f'''<div class="alert-box alert-{level}"><div>
            <strong>{escape(status.category)}:</strong> {escape(detail)}</div>
            <span class="essential-pill pill-{level}">{title}</span></div>''', unsafe_allow_html=True)


def _metrics(summary, budgets):
    total = budgets.get(TOTAL_BUDGET_CATEGORY)
    expense_hint = f"Đã dùng {total.ratio:.1%} ngân sách tháng" if total else "Chưa đặt ngân sách tổng"
    budget_hint = _status_text(total)[2] if total else "Thiết lập trong tab Ngân sách"
    cards = [
        ("Tổng thu nhập", money(summary["income"]), "💰", "#15803D", "#DCFCE7", "Gia đình, làm thêm và học bổng"),
        ("Tổng chi tiêu", money(summary["expense"]), "💸", "#B91C1C", "#FEE2E2", expense_hint),
        ("Chênh lệch thu chi", money(summary["balance"]), "🏦", "#2563EB" if summary["balance"] >= 0 else "#DC2626", "#DBEAFE", "Thu nhập trừ chi tiêu trong tháng"),
        ("Ngân sách tháng", money(total.limit) if total else "Chưa thiết lập", "🎯", "#4F46E5", "#EDE9FE", budget_hint),
    ]
    for column, (title, value, icon, color, tint, hint) in zip(st.columns(4), cards):
        with column:
            st.markdown(f'''<div class="kpi-card"><div class="kpi-top">
                <span class="kpi-label">{title}</span><div class="kpi-icon" style="background:{tint}">{icon}</div></div>
                <div class="kpi-value" style="color:{color}">{value}</div>
                <div class="kpi-sub">{hint}</div></div>''', unsafe_allow_html=True)


def _overview(store, month, summary, budgets):
    st.markdown('<div class="section-heading">🍜 Theo dõi 3 khoản chi thiết yếu</div>', unsafe_allow_html=True)
    totals = store.category_totals(month)
    for column, category in zip(st.columns(3), ("Ăn uống", "Tiền trọ", "Đi lại")):
        icon, title, color, description = CATEGORY_META[category]
        spent = totals[category]
        status = budgets.get(category)
        share = spent / summary["expense"] * 100 if summary["expense"] else 0
        if status:
            level, badge, detail = _status_text(status)
            limit = money(status.limit)
            progress = min(100, status.ratio * 100)
            if level != "safe":
                color = "#DC2626" if level == "danger" else "#D97706"
        else:
            level, badge, detail, limit, progress = "neutral", "Chưa đặt hạn mức", "Đặt ngân sách để theo dõi tiến độ", "Chưa thiết lập", 0
        with column:
            st.markdown(f'''<div class="essential-card"><div class="essential-header">
                <div class="essential-title">{icon} {title}</div><span class="essential-pill pill-{level}">{badge}</span></div>
                <div class="essential-amount">{money(spent)}</div>
                <div class="essential-limit">Định mức: <strong>{limit}</strong> · Chiếm <strong>{share:.1f}%</strong> tổng chi</div>
                <div class="progress-track"><div class="progress-fill" style="width:{progress:.1f}%;background:{color}"></div></div>
                <div class="essential-note">{detail}</div><div class="essential-desc">{description}</div></div>''', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">📌 Tổng hợp chi tiêu trong tháng</div>', unsafe_allow_html=True)
    left, right = st.columns([1.25, 1])
    with left:
        rows = []
        for category, spent in totals.items():
            status = budgets.get(category)
            rows.append({"Danh mục": _category_label(category), "Đã chi (VNĐ)": spent,
                         "Định mức (VNĐ)": status.limit if status else None,
                         "Tỷ lệ dùng (%)": round(status.ratio * 100, 1) if status else None,
                         "Tỷ trọng (%)": round(spent / summary["expense"] * 100, 1) if summary["expense"] else 0})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
            "Đã chi (VNĐ)": st.column_config.NumberColumn(format="localized"),
            "Định mức (VNĐ)": st.column_config.NumberColumn(format="localized"),
            "Tỷ lệ dùng (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "Tỷ trọng (%)": st.column_config.NumberColumn(format="%.1f%%"),
        })
        st.caption(f"{summary['count']} giao dịch thu và chi trong tháng đang chọn.")
    with right:
        if summary["expense"]:
            st.altair_chart(charts.category_donut(totals), width="stretch")
        else:
            st.info("Chưa có chi tiêu trong tháng này. Thêm giao dịch ở thanh bên để bắt đầu.")


def _charts(store, month):
    st.markdown('<div class="section-heading">📈 Biểu đồ chi tiêu theo tháng & xu hướng</div>', unsafe_allow_html=True)
    year, number = map(int, month.split("-"))
    count = min(6, (year - 1) * 12 + number)
    monthly = store.monthly_totals(month, count=count)
    months = [row["month"] for row in monthly]
    records = [record for record in store.list_transactions() if months[0] <= record.date[:7] <= month]
    st.caption("6 tháng gần nhất, kết thúc ở tháng đang chọn. Di chuột lên biểu đồ để xem số tiền.")
    if not records:
        st.info("Chưa có giao dịch trong khoảng thời gian này.")
        return
    left, right = st.columns(2)
    with left:
        st.altair_chart(charts.monthly_income_expense(monthly), width="stretch")
    with right:
        st.altair_chart(charts.monthly_categories(records, months), width="stretch")
    st.markdown('<div class="section-heading">🍜 Biến động Tiền ăn · Tiền trọ · Đi lại</div>', unsafe_allow_html=True)
    st.altair_chart(charts.essential_trend(records, months), width="stretch")
    st.markdown(f'<div class="section-heading">📅 Chi tiêu hằng ngày — {month}</div>', unsafe_allow_html=True)
    st.altair_chart(charts.daily_expenses(records, month), width="stretch")


def _budgets(store, month, statuses, budgets):
    st.markdown(f'<div class="section-heading">🚨 Kiểm soát & thiết lập ngân sách — {month}</div>', unsafe_allow_html=True)
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("#### 📋 Tình hình ngân sách")
        _alerts(statuses, detailed=True)
        category_statuses = [status for status in statuses if status.category != TOTAL_BUDGET_CATEGORY]
        if category_statuses:
            st.altair_chart(charts.budget_comparison(category_statuses), width="stretch")
    with right:
        with st.container(border=True):
            st.markdown("#### ⚙️ Điều chỉnh định mức")
            st.caption("Từ 80%: cảnh báo vàng. Vượt 100%: báo động đỏ. Nhập 0 để bỏ hạn mức.")
            with st.form(f"budget_{month}", enter_to_submit=False):
                amounts = {}
                for category in (TOTAL_BUDGET_CATEGORY, *EXPENSE_CATEGORIES):
                    title = "🎯 Tổng ngân sách tháng (VNĐ)" if category == TOTAL_BUDGET_CATEGORY else f"{_category_label(category)} (VNĐ)"
                    current = budgets.get(category)
                    amounts[category] = st.number_input(title, min_value=0, max_value=MAX_AMOUNT,
                                                        value=current.limit if current else 0, step=50_000,
                                                        format="%d", key=f"budget_{month}_{category}")
                if st.form_submit_button("💾 Lưu ngân sách", type="primary", width="stretch"):
                    try:
                        store.set_budgets(month, amounts)
                    except (ValueError, sqlite3.Error) as exc:
                        st.error(f"Không lưu được ngân sách: {exc}")
                    else:
                        _notice(f"Đã lưu ngân sách tháng {month}.")


def _csv_bytes(records):
    """CSV cho Excel, cùng quy tắc chống công thức như ExpenseStore.export_csv."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(("Mã", "Ngày", "Loại", "Danh mục", "Số tiền (VNĐ)", "Ghi chú"))
    for record in records:
        note = record.note
        if note.lstrip().startswith(("=", "+", "-", "@")):
            note = "'" + note
        writer.writerow((record.id, record.date, TYPE_LABELS[record.kind], record.category, record.amount, note))
    return stream.getvalue().encode("utf-8-sig")


def _edit_transaction(store, records):
    indexed = {record.id: record for record in records}
    selected_id = st.selectbox("Chọn giao dịch", list(indexed), key="edit_transaction_id",
                               format_func=lambda value: f"#{value} · {indexed[value].date} · {indexed[value].category} · {money(indexed[value].amount)}")
    record = indexed[selected_id]
    # Loại đặt ngoài form để cập nhật ngay danh mục khi người dùng đổi thu/chi.
    kind = st.radio("Loại giao dịch cần sửa", ["expense", "income"],
                    index=0 if record.kind == "expense" else 1,
                    format_func=TYPE_LABELS.get, horizontal=True, key=f"edit_kind_{record.id}")
    categories = EXPENSE_CATEGORIES if kind == "expense" else INCOME_CATEGORIES
    with st.form(f"edit_{record.id}_{kind}", enter_to_submit=False):
        transaction_date = st.date_input("Ngày", value=date.fromisoformat(record.date), min_value=date.min, max_value=date.max)
        category = st.selectbox("Danh mục mới", categories,
                               index=categories.index(record.category) if record.category in categories else 0,
                               format_func=_category_label)
        amount = st.number_input("Số tiền mới (VNĐ)", min_value=0, max_value=MAX_AMOUNT, value=record.amount, format="%d", step=5_000)
        note = st.text_input("Ghi chú mới", value=record.note, max_chars=200)
        if st.form_submit_button("Lưu thay đổi", type="primary", width="stretch"):
            try:
                store.update_transaction(record.id, transaction_date.isoformat(), kind, category, amount, note)
            except (ValueError, sqlite3.Error) as exc:
                st.error(f"Không sửa được giao dịch: {exc}")
            else:
                st.session_state["pending_month"] = transaction_date.strftime("%Y-%m")
                _notice(f"Đã cập nhật giao dịch #{record.id}.")


def _ledger(store, month):
    st.markdown(f'<div class="section-heading">📝 Sổ thu / chi hằng ngày — {month}</div>', unsafe_allow_html=True)
    kind_column, category_column, search_column = st.columns([1, 1.2, 2])
    with kind_column:
        kind_label = st.selectbox("Lọc theo loại", ["Tất cả", "Chi tiêu", "Thu nhập"])
    with category_column:
        category = st.selectbox("Lọc theo danh mục", ["Tất cả", *dict.fromkeys((*EXPENSE_CATEGORIES, *INCOME_CATEGORIES))])
    with search_column:
        keyword = st.text_input("🔍 Tìm theo ghi chú hoặc danh mục", placeholder="Nhập từ khóa…")
    records = store.list_transactions(month=month, kind={"Chi tiêu": "expense", "Thu nhập": "income"}.get(kind_label),
                                      category=category if category != "Tất cả" else None, search=keyword)
    income = sum(record.amount for record in records if record.kind == "income")
    expense = sum(record.amount for record in records if record.kind == "expense")
    info, download = st.columns([3, 1])
    with info:
        st.caption(f"{len(records)} giao dịch · Thu: {money(income)} · Chi: {money(expense)}")
    with download:
        st.download_button("📥 Xuất CSV", _csv_bytes(records), file_name=f"chi_tieu_{month}.csv",
                           mime="text/csv", width="stretch", disabled=not records)
    if not records:
        st.info("Không có giao dịch khớp với bộ lọc. Bạn có thể nhập giao dịch ở thanh bên.")
        return
    st.dataframe(pd.DataFrame([{"Mã GD": record.id, "Ngày": record.date,
                               "Loại": TYPE_LABELS[record.kind], "Danh mục": record.category,
                               "Số tiền (VNĐ)": record.amount, "Ghi chú": record.note} for record in records]),
                 hide_index=True, width="stretch", column_config={
                     "Mã GD": st.column_config.NumberColumn(format="%d"),
                     "Số tiền (VNĐ)": st.column_config.NumberColumn(format="localized"),
                     "Ghi chú": st.column_config.TextColumn(width="large"),
                 })
    with st.expander("✏️ Sửa giao dịch"):
        _edit_transaction(store, records)
    with st.expander("🗑️ Xóa giao dịch nhập nhầm"):
        indexed = {record.id: record for record in records}
        selected_id = st.selectbox("Giao dịch cần xóa", list(indexed), key="delete_transaction_id",
                                   format_func=lambda value: f"#{value} · {indexed[value].date} · {indexed[value].category} · {money(indexed[value].amount)}")
        with st.form(f"delete_{selected_id}", enter_to_submit=False):
            confirmed = st.checkbox(f"Tôi xác nhận xóa giao dịch #{selected_id}.")
            if st.form_submit_button("Xóa giao dịch", width="stretch"):
                if not confirmed:
                    st.warning("Đánh dấu xác nhận trước khi xóa giao dịch.")
                else:
                    try:
                        store.delete_transaction(selected_id)
                    except (ValueError, sqlite3.Error) as exc:
                        st.error(f"Không xóa được giao dịch: {exc}")
                    else:
                        _notice(f"Đã xóa giao dịch #{selected_id}.")


def run_app(db_path, demo=False):
    st.set_page_config(page_title="UniSpend — Quản lý chi tiêu sinh viên", page_icon="🎓",
                       layout="wide", initial_sidebar_state="expanded")
    css = Path(__file__).with_name("theme.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    try:
        store = ExpenseStore(db_path)
    except (OSError, sqlite3.Error) as exc:
        st.error(f"Không mở được dữ liệu: {exc}")
        return
    # Mỗi lần hiển thị dùng một kết nối riêng, đóng cả khi Streamlit rerun.
    try:
        demo_key = f"demo_initialized:{Path(db_path).resolve()}"
        if demo and not st.session_state.get(demo_key):
            store.seed_demo()
            st.session_state[demo_key] = True
        month = _sidebar(store, demo)
        _hero(month, demo)
        notice = st.session_state.pop("notice", None)
        if notice:
            st.success(notice)
        summary = store.summary(month)
        statuses = store.budget_statuses(month)
        budgets = {status.category: status for status in statuses}
        _alerts(statuses)
        _metrics(summary, budgets)
        overview, chart_tab, budget_tab, ledger = st.tabs([
            "📊 Tổng quan", "📈 Biểu đồ theo tháng", "🚨 Cảnh báo & Ngân sách", "📝 Sổ giao dịch"])
        with overview:
            _overview(store, month, summary, budgets)
        with chart_tab:
            _charts(store, month)
        with budget_tab:
            _budgets(store, month, statuses, budgets)
        with ledger:
            _ledger(store, month)
        st.caption("UniSpend · Ghi chép hôm nay, chủ động ngày mai.")
    except (OSError, sqlite3.Error) as exc:
        st.error(f"Không đọc hoặc lưu được dữ liệu: {exc}")
    finally:
        store.close()
