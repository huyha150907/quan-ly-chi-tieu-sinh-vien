"""Giao diện Streamlit của UniSpend."""

from datetime import date
from pathlib import Path
import pandas as pd
import altair as alt
import streamlit as st

# LIÊN KẾT QUA PHẦN BACKEND BÊN IDE
from backend import ExpenseBackend
from database import database_path
from models import EXPENSE_CATEGORIES


# =============================================================================
# 1. CẤU HÌNH TRANG STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="UniSpend · Quản lý chi tiêu sinh viên",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


def format_vnd(amount: float) -> str:
    """Định dạng số tiền sang chuẩn VNĐ dễ đọc (VD: 1.850.000 đ)."""
    return f"{amount:,.0f} đ".replace(",", ".")


st.html(Path(__file__).resolve().with_name("dashboard.css"))


@st.cache_resource
def get_backend(path: str) -> ExpenseBackend:
    return ExpenseBackend(path)


backend = get_backend(str(database_path()))


# =============================================================================
# 4. SIDEBAR: BỘ CHỌN THÁNG, MỨC TIỀN GỢI Ý NHANH & FORM NHẬP THU / CHI
# =============================================================================
if "quick_amount" not in st.session_state:
    st.session_state.quick_amount = 45_000
if st.session_state.pop("quick_clear_note", False):
    st.session_state["quick_note"] = ""


def set_quick_amount(amount):
    """Đổi số tiền trước lượt hiển thị, giữ nguyên nội dung đang nhập."""
    st.session_state["quick_amount"] = amount

with st.sidebar:
    st.html('<div class="sidebar-brand"><span>UTH</span>UniSpend</div>')

    available_months = backend.get_available_months()
    saved_month = st.session_state.pop("report_month_after_save", None)
    if saved_month in available_months:
        st.session_state["report_month"] = saved_month
    elif st.session_state.get("report_month") not in available_months:
        st.session_state["report_month"] = available_months[0]
    selected_month = st.selectbox(
        "Tháng báo cáo",
        options=available_months,
        index=0,
        key="report_month",
    )

    st.markdown("---")
    st.markdown("### Thêm giao dịch")

    tx_type_quick = st.radio(
        "Loại giao dịch:",
        options=["Chi tiêu", "Thu nhập"],
        horizontal=True,
        key="sidebar_tx_type"
    )

    # Nút chọn nhanh mệnh giá tiền phổ biến của sinh viên (Interactive Quick Chips)
    st.caption("Chọn nhanh số tiền")
    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1:
        st.button("35k 🍜", use_container_width=True, help="Cơm trưa / Phở sáng",
                  key="quick_35000", on_click=set_quick_amount, args=(35_000,))
    with q_col2:
        st.button("50k 🛵", use_container_width=True, help="Đổ xăng / Trà sữa",
                  key="quick_50000", on_click=set_quick_amount, args=(50_000,))
    with q_col3:
        st.button("200k 🛒", use_container_width=True, help="Đi siêu thị / Mua sách",
                  key="quick_200000", on_click=set_quick_amount, args=(200_000,))

    cat_dict = backend.get_categories(tx_type_quick)
    cat_options = list(cat_dict.keys())

    category_key = "quick_category_expense" if tx_type_quick == "Chi tiêu" else "quick_category_income"
    # Không trì hoãn dữ liệu trong form: đổi loại hoặc bấm mệnh giá vẫn giữ bản nháp.
    with st.container(border=True):
        selected_cat = st.selectbox(
            "Danh mục:",
            options=cat_options,
            format_func=lambda c: f"{cat_dict[c]['icon']} {c}",
            key=category_key,
        )
        tx_date = st.date_input("Ngày giao dịch:", value=date.today(), key="quick_date")
        tx_amount = st.number_input(
            "Số tiền (VNĐ):",
            min_value=0,
            max_value=500_000_000,
            step=5_000,
            format="%d",
            key="quick_amount",
            help="Nhập số tiền lớn hơn 0 VNĐ"
        )
        tx_note = st.text_input(
            "Ghi chú chi tiết:",
            placeholder="VD: Cơm trưa căn tin, Đổ xăng, Tiền trọ...",
            key="quick_note",
            max_chars=200,
        )

        submitted = st.button("💾 Lưu Giao Dịch Ngay", use_container_width=True, type="primary", key="quick_save")
        if submitted:
            ok, message = backend.add_daily_transaction(
                date_str=tx_date.isoformat(),
                tx_type=tx_type_quick,
                category=selected_cat,
                amount=float(tx_amount),
                note=tx_note
            )
            if ok:
                st.session_state["report_month_after_save"] = tx_date.isoformat()[:7]
                st.session_state["quick_clear_note"] = True
                st.session_state["quick_saved_notice"] = message
                st.rerun()
            else:
                st.error(f"⚠️ {message}")

    saved_notice = st.session_state.pop("quick_saved_notice", None)
    if saved_notice:
        st.success(f"✅ {saved_notice}")

    st.markdown("---")
    with st.expander("Dữ liệu mẫu"):
        reset_confirmed = st.checkbox("Thay giao dịch và ngân sách hiện tại bằng dữ liệu mẫu")
        if st.button("Nạp lại dữ liệu mẫu", use_container_width=True, disabled=not reset_confirmed):
            backend.reset_demo_data()
            st.session_state["report_month_after_save"] = date.today().strftime("%Y-%m")
            st.toast("Đã nạp lại bộ dữ liệu mẫu thành công!", icon="🎉")
            st.rerun()


# =============================================================================
# 5. LẤY DỮ LIỆU TỪ BACKEND CHO THÁNG ĐANG CHỌN
# =============================================================================
dashboard_data = backend.get_monthly_dashboard_data(selected_month)
charts_data = backend.get_charts_data(selected_month)

total_income = dashboard_data["total_income"]
total_expense = dashboard_data["total_expense"]
balance = dashboard_data["balance"]
total_budget = dashboard_data["total_budget"]
budget_used_pct = dashboard_data["budget_used_pct"]
budget_remaining = dashboard_data["budget_remaining"]
budget_cfg = dashboard_data["budget_config"]
alerts = dashboard_data["alerts"]
essential_stats = dashboard_data["essential_stats"]
df_category_summary = dashboard_data["df_category_summary"]
df_month = dashboard_data["df_month"]


y_str, m_str = selected_month.split("-")
budget_progress = max(0, min(budget_used_pct, 100))

st.html(f"""
<section class="dashboard-hero" aria-labelledby="dashboard-title">
    <div>
        <p class="hero-period">Báo cáo tháng {m_str}/{y_str}</p>
        <h1 id="dashboard-title">Quản lý chi tiêu sinh viên</h1>
    </div>
    <div class="wallet-panel">
        <span>Ngân sách còn lại</span>
        <strong>{format_vnd(budget_remaining)}</strong>
        <div class="progress-track-3d" aria-hidden="true">
            <div class="progress-fill-3d" style="width: {budget_progress:.1f}%"></div>
        </div>
        <span>Đã dùng {budget_used_pct:.1f}% · {len(df_month)} giao dịch</span>
    </div>
</section>
""")


# =============================================================================
# 7. HỆ THỐNG CẢNH BÁO NGÂN SÁCH TỨC THỜI (3D PULSE ALERTS)
# =============================================================================
danger_count = sum(alert["level"] == "danger" for alert in alerts)
warning_count = sum(alert["level"] == "warning" for alert in alerts)
if danger_count or warning_count:
    summaries = []
    if danger_count:
        summaries.append(f"{danger_count} mục vượt ngân sách")
    if warning_count:
        summaries.append(f"{warning_count} mục sắp chạm ngưỡng")
    status = "danger" if danger_count else "warning"
    st.html(f"""
    <div class="alert-box-3d alert-{status}-3d">
        <strong>{' · '.join(summaries)}</strong>
        <span>Xem chi tiết ở tab Ngân sách</span>
    </div>
    """)


# =============================================================================
# 8. 4 THẺ CHỈ SỐ TÀI CHÍNH 3D TƯƠNG TÁC (3D TILT KPI CARDS)
# =============================================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="kpi-card-3d">
        <div class="kpi-top-3d">
            <span class="kpi-label-3d">Tổng Thu Nhập</span>
            <div class="kpi-icon-3d" style="background:linear-gradient(135deg,#DCFCE7,#86EFAC); color:#15803D;">💰</div>
        </div>
        <div class="kpi-value-3d" style="color:#15803D;">{format_vnd(total_income)}</div>
        <div class="kpi-sub-3d" style="color:#64748B;">Trợ cấp gia đình, làm thêm, học bổng</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card-3d">
        <div class="kpi-top-3d">
            <span class="kpi-label-3d">Tổng Chi Tiêu</span>
            <div class="kpi-icon-3d" style="background:linear-gradient(135deg,#FEE2E2,#FCA5A5); color:#B91C1C;">💸</div>
        </div>
        <div class="kpi-value-3d" style="color:#B91C1C;">{format_vnd(total_expense)}</div>
        <div class="kpi-sub-3d" style="color:#64748B;">Đã dùng <strong>{budget_used_pct:.1f}%</strong> ngân sách tháng</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    bal_color = "#0F172A" if balance >= 0 else "#DC2626"
    bal_sub = "Thu trừ chi trong tháng" if balance >= 0 else "Chi vượt tổng thu nhập!"
    st.markdown(f"""
    <div class="kpi-card-3d">
        <div class="kpi-top-3d">
            <span class="kpi-label-3d">Số Dư Thực Tế</span>
            <div class="kpi-icon-3d" style="background:linear-gradient(135deg,#DBEAFE,#93C5FD); color:#1D4ED8;">🏦</div>
        </div>
        <div class="kpi-value-3d" style="color:{bal_color};">{format_vnd(balance)}</div>
        <div class="kpi-sub-3d" style="color:#64748B;">{bal_sub}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    rem_color = "#16A34A" if budget_remaining >= 0 else "#DC2626"
    rem_label = f"Còn được tiêu: {format_vnd(budget_remaining)}" if budget_remaining >= 0 else f"Vượt định mức: {format_vnd(abs(budget_remaining))}"
    st.markdown(f"""
    <div class="kpi-card-3d">
        <div class="kpi-top-3d">
            <span class="kpi-label-3d">Ngân Sách Tháng</span>
            <div class="kpi-icon-3d" style="background:linear-gradient(135deg,#FEF3C7,#FCD34D); color:#B45309;">🎯</div>
        </div>
        <div class="kpi-value-3d" style="color:#4F46E5;">{format_vnd(total_budget)}</div>
        <div class="kpi-sub-3d" style="color:{rem_color}; font-weight:700;">{rem_label}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")


# =============================================================================
# 9. CÁC TAB CHỨC NĂNG TƯƠNG TÁC TRÊN GIAO DIỆN
# =============================================================================
tab_overview, tab_ledger, tab_charts, tab_simulator, tab_tasks = st.tabs([
    "Tổng quan",
    "Sổ thu chi",
    "Biểu đồ",
    "Ngân sách",
    "Việc cần làm",
])


# -----------------------------------------------------------------------------
# TAB 1: THỐNG KÊ 3D TIỀN ĂN, TIỀN TRỌ, ĐI LẠI
# -----------------------------------------------------------------------------
with tab_overview:
    st.markdown('<div class="section-heading-3d">Chi tiêu thiết yếu</div>', unsafe_allow_html=True)

    c_cols = st.columns(3)
    icon_bgs = [
        "linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%)",
        "linear-gradient(135deg, #CCFBF1 0%, #99F6E4 100%)",
        "linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%)",
    ]

    for idx, item in enumerate(essential_stats):
        bar_width = min(item["percent"], 100.0)
        if item["status"] == "danger":
            pill_cls = "pill-danger"
            fill_gradient = "linear-gradient(90deg, #EF4444, #FB7185, #EF4444)"
        elif item["status"] == "warning":
            pill_cls = "pill-warning"
            fill_gradient = "linear-gradient(90deg, #F59E0B, #FBBF24, #F59E0B)"
        else:
            pill_cls = "pill-safe"
            fill_gradient = "linear-gradient(90deg, #10B981, #34D399, #10B981)"

        with c_cols[idx]:
            st.markdown(f"""
            <div class="essential-card-3d">
                <div class="essential-header-3d">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <div class="essential-icon-badge" style="background:{icon_bgs[idx]};">{item['icon']}</div>
                        <div class="essential-title-text">{item['category']}</div>
                    </div>
                    <span class="essential-pill {pill_cls}">{item['badge_text']}</span>
                </div>
                <div class="essential-amount-3d">{format_vnd(item['spent'])}</div>
                <div class="essential-limit-3d">
                    Định mức: <strong>{format_vnd(item['limit'])}</strong> • Chiếm <strong>{item['share_of_total']:.1f}%</strong> tổng chi
                </div>
                <div class="progress-track-3d">
                    <div class="progress-fill-3d" style="width: {bar_width:.1f}%; background-image: {fill_gradient};"></div>
                </div>
                <div style="font-size: 0.84rem; font-weight: 700; color: #334155; margin-bottom: 4px;">
                    {item['note_text']}
                </div>
                <div style="font-size: 0.77rem; color: #566881;">{item['desc']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-heading-3d">Chi tiêu theo danh mục</div>', unsafe_allow_html=True)
    left_col, right_col = st.columns([1.25, 1])

    with left_col:
        st.dataframe(
            df_category_summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Đã chi (VNĐ)": st.column_config.NumberColumn(format="%d đ"),
                "Định mức (VNĐ)": st.column_config.NumberColumn(format="%d đ"),
                "Tỷ lệ dùng (%)": st.column_config.ProgressColumn(
                    "Mức sử dụng ngân sách",
                    format="%.1f%%",
                    min_value=0,
                    max_value=120,
                ),
                "Tỷ trọng (%)": st.column_config.NumberColumn(format="%.1f%%"),
            }
        )

    with right_col:
        df_pie = charts_data["pie_month"]
        if not df_pie.empty:
            hover_sel = alt.selection_point(on="mouseover", nearest=True, empty=False)
            donut_chart = (
                alt.Chart(df_pie)
                .mark_arc(innerRadius=62, outerRadius=118, cornerRadius=8, padAngle=0.02)
                .encode(
                    theta=alt.Theta(field="amount", type="quantitative"),
                    color=alt.Color("category:N", title="Danh mục", scale=alt.Scale(scheme="tableau10")),
                    opacity=alt.condition(hover_sel, alt.value(1.0), alt.value(0.85)),
                    strokeWidth=alt.condition(hover_sel, alt.value(3), alt.value(0)),
                    stroke=alt.value("#1E1B4B"),
                    tooltip=[
                        alt.Tooltip("category:N", title="Danh mục"),
                        alt.Tooltip("amount:Q", title="Số tiền (VNĐ)", format=",.0f"),
                        alt.Tooltip("pct:Q", title="Tỷ trọng (%)", format=".1f"),
                    ]
                )
                .add_params(hover_sel)
                .properties(height=320, title=f"Cơ cấu chi tiêu tháng {selected_month}")
            )
            st.altair_chart(donut_chart, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu chi tiêu trong tháng này.")


# -----------------------------------------------------------------------------
# TAB 2: BIỂU ĐỒ CHI TIÊU THEO THÁNG (TƯƠNG TÁC ZOOM, FILTER, HOVER)
# -----------------------------------------------------------------------------
with tab_charts:
    st.markdown('<div class="section-heading-3d">Xu hướng thu chi theo tháng</div>', unsafe_allow_html=True)

    df_monthly_io = charts_data["monthly_io"]
    df_monthly_cat = charts_data["monthly_cat"]
    df_core3_trend = charts_data["core3_trend"]
    df_daily = charts_data["daily_expense"]

    if not df_monthly_io.empty:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            bar_hover = alt.selection_point(on="mouseover", empty=True)
            bar_io = (
                alt.Chart(df_monthly_io)
                .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7, size=28)
                .encode(
                    x=alt.X("month:N", title="Tháng (YYYY-MM)", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("amount:Q", title="Số tiền (VNĐ)"),
                    xOffset="tx_type:N",
                    color=alt.Color(
                        "tx_type:N",
                        title="Loại giao dịch",
                        scale=alt.Scale(domain=["Thu nhập", "Chi tiêu"], range=["#10B981", "#EF4444"])
                    ),
                    opacity=alt.condition(bar_hover, alt.value(1.0), alt.value(0.75)),
                    tooltip=[
                        alt.Tooltip("month:N", title="Tháng"),
                        alt.Tooltip("tx_type:N", title="Loại"),
                        alt.Tooltip("amount:Q", title="Tổng tiền (VNĐ)", format=",.0f"),
                    ]
                )
                .add_params(bar_hover)
                .properties(height=340, title="So sánh Tổng Thu Nhập và Tổng Chi Tiêu theo Tháng")
                .interactive()
            )
            st.altair_chart(bar_io, use_container_width=True)

        with chart_col2:
            legend_click = alt.selection_point(fields=["category"], bind="legend")
            stacked_bar = (
                alt.Chart(df_monthly_cat)
                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=38)
                .encode(
                    x=alt.X("month:N", title="Tháng (YYYY-MM)", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("amount:Q", title="Chi tiêu (VNĐ)"),
                    color=alt.Color("category:N", title="Danh mục (Bấm để lọc)", scale=alt.Scale(scheme="category10")),
                    opacity=alt.condition(legend_click, alt.value(1.0), alt.value(0.2)),
                    tooltip=[
                        alt.Tooltip("month:N", title="Tháng"),
                        alt.Tooltip("category:N", title="Danh mục"),
                        alt.Tooltip("amount:Q", title="Chi tiêu (VNĐ)", format=",.0f"),
                    ]
                )
                .add_params(legend_click)
                .properties(height=340, title="Chi tiêu theo Tháng (Bấm vào Chú thích để lọc riêng danh mục)")
            )
            st.altair_chart(stacked_bar, use_container_width=True)

        st.markdown('<div class="section-heading-3d">🍜 Biểu đồ biến động Tiền Ăn • Tiền Trọ • Đi Lại qua các tháng</div>', unsafe_allow_html=True)
        if not df_core3_trend.empty:
            line_core = (
                alt.Chart(df_core3_trend)
                .mark_line(point=alt.OverlayMarkDef(size=110, filled=True), strokeWidth=3.5, interpolate="monotone")
                .encode(
                    x=alt.X("month:N", title="Tháng", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("amount:Q", title="Số tiền (VNĐ)"),
                    color=alt.Color(
                        "category:N",
                        title="Khoản thiết yếu",
                        scale=alt.Scale(
                            domain=["Tiền ăn", "Tiền trọ", "Đi lại"],
                            range=["#EF4444", "#0D9488", "#2563EB"]
                        )
                    ),
                    tooltip=[
                        alt.Tooltip("month:N", title="Tháng"),
                        alt.Tooltip("category:N", title="Danh mục"),
                        alt.Tooltip("amount:Q", title="Số tiền (VNĐ)", format=",.0f"),
                    ]
                )
                .properties(height=300)
                .interactive()
            )
            st.altair_chart(line_core, use_container_width=True)

        st.markdown(f'<div class="section-heading-3d">📅 Biểu đồ nhịp độ chi tiêu hằng ngày trong tháng {selected_month}</div>', unsafe_allow_html=True)
        if not df_daily.empty:
            area_daily = (
                alt.Chart(df_daily)
                .mark_area(
                    interpolate="monotone",
                    line={"color": "#4F46E5", "strokeWidth": 3},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[
                            alt.GradientStop(color="rgba(79, 70, 229, 0.50)", offset=0),
                            alt.GradientStop(color="rgba(79, 70, 229, 0.02)", offset=1),
                        ],
                        x1=1, x2=1, y1=1, y2=0,
                    ),
                    point=alt.OverlayMarkDef(color="#4F46E5", size=80)
                )
                .encode(
                    x=alt.X("date:N", title="Ngày trong tháng", axis=alt.Axis(labelAngle=-30)),
                    y=alt.Y("amount:Q", title="Chi tiêu trong ngày (VNĐ)"),
                    tooltip=[
                        alt.Tooltip("date:N", title="Ngày"),
                        alt.Tooltip("amount:Q", title="Tổng chi (VNĐ)", format=",.0f"),
                    ]
                )
                .properties(height=280)
                .interactive()
            )
            st.altair_chart(area_daily, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 3: TRÌNH GIẢ LẬP TƯƠNG TÁC (WHAT-IF SIMULATOR) & CÀI ĐẶT NGÂN SÁCH
# -----------------------------------------------------------------------------
with tab_simulator:
    st.markdown(f'<div class="section-heading-3d">🎛️ Trình Giả Lập Chi Tiêu Tương Tác (What-If Simulator) — Tháng {selected_month}</div>', unsafe_allow_html=True)
    st.caption("Kéo các thanh trượt bên dưới để xem ngay lập tức việc tăng/giảm Tiền ăn, Tiền trọ, Đi lại sẽ ảnh hưởng thế nào đến Số dư cuối tháng!")

    sim_col1, sim_col2 = st.columns([1.15, 1])
    with sim_col1:
        food_spent, rent_spent, move_spent = (int(item["spent"]) for item in essential_stats[:3])
        sim_food = st.slider(
            "🍜 Giả lập Tiền ăn trong tháng (VNĐ):",
            min_value=0,
            max_value=max(5_000_000, food_spent),
            value=food_spent,
            step=50_000
        )
        sim_rent = st.slider(
            "🏠 Giả lập Tiền trọ + Điện nước (VNĐ):",
            min_value=0,
            max_value=max(5_000_000, rent_spent),
            value=rent_spent,
            step=50_000
        )
        sim_move = st.slider(
            "🛵 Giả lập Tiền đi lại + Xăng xe (VNĐ):",
            min_value=0,
            max_value=max(2_000_000, move_spent),
            value=move_spent,
            step=25_000
        )

    with sim_col2:
        other_spent = total_expense - sum(x["spent"] for x in essential_stats)
        sim_total_exp = sim_food + sim_rent + sim_move + max(0.0, other_spent)
        sim_balance = total_income - sim_total_exp
        sim_vs_budget = total_budget - sim_total_exp
        sim_pct = (sim_total_exp / total_budget * 100) if total_budget > 0 else 0.0

        sim_card_color = "#16A34A" if sim_vs_budget >= 0 else "#DC2626"
        sim_status_msg = (
            f"✅ Tiết kiệm được {format_vnd(sim_vs_budget)} so với ngân sách!"
            if sim_vs_budget >= 0
            else f"🚨 Vượt ngân sách tháng {format_vnd(abs(sim_vs_budget))}!"
        )

        st.markdown(f"""
        <div class="essential-card-3d" style="border: 2px solid {sim_card_color};">
            <div style="font-size:0.8rem; font-weight:700; text-transform:uppercase; color:#64748B; margin-bottom:6px;">
                🔮 KẾT QUẢ DỰ BÁO TỨC THỜI (REAL-TIME SIMULATION)
            </div>
            <div style="font-size:1.75rem; font-weight:800; color:{sim_card_color}; margin-bottom:6px;">
                Tổng chi dự kiến: {format_vnd(sim_total_exp)}
            </div>
            <div style="font-size:0.92rem; color:#1E293B; margin-bottom:12px;">
                Số dư cuối tháng dự kiến: <strong>{format_vnd(sim_balance)}</strong> ({sim_pct:.1f}% ngân sách)
            </div>
            <div class="progress-track-3d">
                <div class="progress-fill-3d" style="width:{min(sim_pct, 100):.1f}%; background-image:linear-gradient(90deg, #4F46E5, #EC4899, #4F46E5);"></div>
            </div>
            <div style="font-size:0.9rem; font-weight:700; color:{sim_card_color}; margin-top:8px;">
                {sim_status_msg}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f'<div class="section-heading-3d">🚨 Chi tiết Cảnh báo & Cài đặt Ngân sách Tháng {selected_month}</div>', unsafe_allow_html=True)

    b_col1, b_col2 = st.columns([1.1, 1])

    with b_col1:
        st.markdown("#### 📋 Danh sách cảnh báo từ Backend")
        for a in alerts:
            if a["level"] == "danger":
                st.error(f"🚨 **{a['scope']}**: {a['message']}")
            elif a["level"] == "warning":
                st.warning(f"⚠️ **{a['scope']}**: {a['message']}")
            else:
                st.success(f"✅ **{a['scope']}**: {a['message']}")

        compare_rows = []
        spent_by_cat = dashboard_data["spent_by_cat"]
        for cat in EXPENSE_CATEGORIES:
            compare_rows.append({
                "Danh mục": cat,
                "Loại": "1. Đã chi thực tế",
                "Số tiền": spent_by_cat.get(cat, 0.0)
            })
            compare_rows.append({
                "Danh mục": cat,
                "Loại": "2. Định mức tối đa",
                "Số tiền": budget_cfg.category_limits.get(cat, 0.0)
            })
        df_cmp = pd.DataFrame(compare_rows)
        cmp_chart = (
            alt.Chart(df_cmp)
            .mark_bar(cornerRadiusEnd=6)
            .encode(
                y=alt.Y("Danh mục:N", title=None, sort="-x"),
                x=alt.X("Số tiền:Q", title="Số tiền (VNĐ)"),
                yOffset="Loại:N",
                color=alt.Color(
                    "Loại:N",
                    scale=alt.Scale(
                        domain=["1. Đã chi thực tế", "2. Định mức tối đa"],
                        range=["#EF4444", "#94A3B8"]
                    )
                ),
                tooltip=[
                    alt.Tooltip("Danh mục:N"),
                    alt.Tooltip("Loại:N"),
                    alt.Tooltip("Số tiền:Q", format=",.0f"),
                ]
            )
            .properties(height=320, title="So sánh Chi tiêu thực tế với Định mức Ngân sách")
        )
        st.altair_chart(cmp_chart, use_container_width=True)

    with b_col2:
        st.markdown(f"#### ⚙️ Điều chỉnh Định mức Ngân sách ({selected_month})")
        st.caption("Khi đạt 80% định mức: Cảnh báo vàng. Khi vượt 100% định mức: Báo động đỏ.")

        with st.form(f"budget_settings_form_{selected_month}", enter_to_submit=False):
            new_total_budget = st.number_input(
                "🎯 Tổng ngân sách chi tiêu tối đa trong tháng (VNĐ):",
                min_value=500_000,
                max_value=100_000_000,
                value=int(budget_cfg.total_budget),
                step=100_000,
                key=f"total_budget_{selected_month}",
            )
            st.markdown("**Định mức riêng cho từng hạng mục:**")
            new_limits = {}
            for cat, meta in EXPENSE_CATEGORIES.items():
                cur_limit = int(budget_cfg.category_limits.get(cat, 300_000))
                new_limits[cat] = float(
                    st.number_input(
                        f"{meta['icon']} Định mức {cat} (VNĐ):",
                        min_value=0,
                        max_value=50_000_000,
                        value=cur_limit,
                        step=50_000,
                        key=f"limit_{selected_month}_{cat}"
                    )
                )

            save_budget_btn = st.form_submit_button("💾 Lưu Cấu Hình Xuống Backend", use_container_width=True, type="primary")
            if save_budget_btn:
                backend.update_budget(
                    month=selected_month,
                    total_budget=float(new_total_budget),
                    category_limits=new_limits
                )
                st.toast("Đã lưu cấu hình ngân sách mới!", icon="✅")
                st.success("✅ Đã lưu định mức ngân sách mới thành công!")
                st.rerun()


# -----------------------------------------------------------------------------
# TAB 4: SỔ GIAO DỊCH HẰNG NGÀY (THU / CHI)
# -----------------------------------------------------------------------------
with tab_ledger:
    st.markdown(f'<div class="section-heading-3d">Giao dịch tháng {m_str}/{y_str}</div>', unsafe_allow_html=True)

    f_col1, f_col2, f_col3, f_col4 = st.columns([1.2, 1.4, 1.8, 1])
    with f_col1:
        filter_type = st.selectbox("Lọc theo loại:", ["Tất cả", "Chi tiêu", "Thu nhập"], key="ledger_type")
    with f_col2:
        all_cats_in_month = ["Tất cả"] + sorted(df_month["category"].unique().tolist()) if not df_month.empty else ["Tất cả"]
        filter_cat = st.selectbox("Lọc theo danh mục:", all_cats_in_month)
    with f_col3:
        search_kw = st.text_input("🔍 Tìm theo ghi chú:", placeholder="Nhập từ khóa (VD: xăng, cơm, trọ...)", key="ledger_search")
    with f_col4:
        st.write("")
        if not df_month.empty:
            csv_bytes = df_month.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 Xuất file CSV",
                data=csv_bytes,
                file_name=f"chi_tieu_sinh_vien_{selected_month}.csv",
                mime="text/csv",
                use_container_width=True
            )

    df_filtered = df_month.copy()
    if filter_type != "Tất cả":
        df_filtered = df_filtered[df_filtered["tx_type"] == filter_type]
    if filter_cat != "Tất cả":
        df_filtered = df_filtered[df_filtered["category"] == filter_cat]
    if search_kw.strip():
        df_filtered = df_filtered[df_filtered["note"].str.contains(search_kw.strip(), case=False, na=False, regex=False)]

    if not df_filtered.empty:
        st.dataframe(
            df_filtered[["id", "date", "tx_type", "category", "amount", "note"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("Mã GD", width="small"),
                "date": st.column_config.TextColumn("Ngày (YYYY-MM-DD)"),
                "tx_type": st.column_config.TextColumn("Loại giao dịch"),
                "category": st.column_config.TextColumn("Danh mục"),
                "amount": st.column_config.NumberColumn("Số tiền (VNĐ)", format="%d đ"),
                "note": st.column_config.TextColumn("Ghi chú chi tiết", width="large"),
            }
        )

        with st.expander("🗑️ Xóa giao dịch nhập nhầm"):
            del_col1, del_col2 = st.columns([3, 1])
            with del_col1:
                tx_options = {
                    row["id"]: f"#{row['id']} | {row['date']} | {row['tx_type']} - {row['category']} | {format_vnd(row['amount'])} ({row['note']})"
                    for _, row in df_filtered.iterrows()
                }
                selected_del_id = st.selectbox(
                    "Chọn giao dịch cần xóa:",
                    options=list(tx_options.keys()),
                    format_func=lambda x: tx_options[x]
                )
            with del_col2:
                st.write("")
                if st.button("🗑️ Xóa giao dịch này", type="secondary", use_container_width=True):
                    if backend.remove_transaction(int(selected_del_id)):
                        st.toast(f"Đã xóa giao dịch #{selected_del_id}!", icon="🗑️")
                        st.success(f"Đã xóa giao dịch #{selected_del_id}!")
                        st.rerun()
    else:
        st.info("Không tìm thấy giao dịch nào khớp với bộ lọc hiện tại.")


with tab_tasks:
    if "student_todos" not in st.session_state:
        st.session_state.student_todos = [
            {"title": "Nộp bài xác suất", "due": "20/11", "priority": "Cao", "done": False},
            {"title": "Đóng tiền trọ tháng này", "due": "25/11", "priority": "Vừa", "done": False},
            {"title": "Mua giáo trình Python", "due": "15/11", "priority": "Thấp", "done": True},
        ]
    tasks = st.session_state.student_todos
    task_form, task_list = st.columns([1, 1.35])
    with task_form, st.form("add_todo", clear_on_submit=True):
        title = st.text_input("Tên công việc", max_chars=120, key="todo_title")
        due = st.text_input("Hạn chót", placeholder="VD: 30/11", max_chars=20)
        priority = st.selectbox("Ưu tiên", ("Vừa", "Cao", "Thấp"))
        if st.form_submit_button("Thêm công việc", type="primary"):
            if title.strip():
                tasks.append({"title": title.strip(), "due": due.strip(), "priority": priority, "done": False})
            else:
                st.error("Nhập tên công việc.")
    with task_list:
        done = sum(task["done"] for task in tasks)
        st.progress(done / len(tasks), text=f"Đã hoàn thành {done}/{len(tasks)} công việc")
        for index, task in enumerate(tasks):
            with st.container(border=True):
                if st.checkbox(task["title"], value=task["done"], key=f"todo_check_{index}") != task["done"]:
                    task["done"] = not task["done"]
                    st.rerun()
                detail = f"Hạn {task['due']} · " if task["due"] else ""
                st.caption(f"{detail}Ưu tiên {task['priority'].lower()}")
