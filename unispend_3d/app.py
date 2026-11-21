# -*- coding: utf-8 -*-
"""
Module app.py (Giao diện UTH Spend — Phong cách Dark/Light Emerald Money Calendar + Hiệu ứng 3D)
-------------------------------------------------------------------------
Thiết kế dựa theo giao diện mẫu https://thuvien01.streamlit.app/:
- Nền tối Charcoal-Emerald (#070E0B / #0F1C17) sang trọng (có nút chuyển Light Mode).
- Sidebar điều hướng cố định bên trái với hiệu ứng phát sáng Emerald (#10B981),
  thẻ Gợi ý thông minh và nút chuyển Dark/Light Mode.
- Header điều hướng tháng (< Tháng MM, YYYY >), nút Hôm nay, Ghi nhanh.
- 4 Thẻ KPI có biểu đồ Sparkline mini + hiệu ứng nghiêng 3D theo con trỏ chuột.
- Lịch tài chính 7 cột (T2 - CN) tô màu theo mức chi tiêu từng ngày, bấm vào
  từng ngày để xem chi tiết giao dịch ngày đó + hộp Cảnh báo Chi tiêu an toàn.
- Thống kê chuyên sâu Tiền ăn • Tiền trọ • Đi lại, Biểu đồ theo tháng,
  Nhập/Xuất CSV rõ ràng từng dòng và Giả lập Ngân sách.
- Liên kết 100% dữ liệu thật với `backend.py` & SQLite (`student_expense.db`).
"""

import base64
import calendar
import os
from csv import Error as CsvError
from datetime import date, datetime
from html import escape
from sqlite3 import Error as DatabaseError
import pandas as pd
import altair as alt
import streamlit as st
import streamlit.components.v1 as components

# LIÊN KẾT QUA PHẦN BACKEND BÊN IDE
if __package__:
    from .backend import ExpenseBackend
    from .csv_import import read_transactions_csv
    from .database import database_path
    from .models import EXPENSE_CATEGORIES
else:
    from backend import ExpenseBackend
    from csv_import import read_transactions_csv
    from database import database_path
    from models import EXPENSE_CATEGORIES


# =============================================================================
# 1. CẤU HÌNH TRANG STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="UTH — Quản Lý Chi Tiêu Sinh Viên",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded",
)


def format_vnd(amount: float) -> str:
    """Định dạng số tiền chuẩn VNĐ (VD: 1.250.000 đ)."""
    return f"{amount:,.0f} đ".replace(",", ".")


def format_compact_vnd(amount: float) -> str:
    """Định dạng gọn cho ô lịch (VD: -450k hoặc -1,8tr)."""
    abs_a = abs(amount)
    sign = "-" if amount > 0 else ""
    if abs_a >= 1_000_000:
        return f"{sign}{abs_a / 1_000_000:.1f}tr".replace(".", ",")
    if abs_a >= 1_000:
        return f"{sign}{int(round(abs_a / 1_000))}k"
    return f"{sign}{int(abs_a)}đ"


# =============================================================================
# 2. HỆ THỐNG CSS DARK/LIGHT EMERALD + HIỆU ỨNG ĐỘNG & 3D ENGINE
# =============================================================================
def inject_emerald_3d_theme(is_dark: bool):
    if is_dark:
        bg_app = "#0F1226"
        bg_sidebar = "#141833"
        bg_card = "#1A1F42"
        bg_card_2 = "#212752"
        border_col = "#2E366D"
        text_main = "#F8FAFC"
        text_muted = "#A5B4FC"
        accent = "#8B5CF6"
        accent_soft = "rgba(139, 92, 246, 0.16)"
        red_bg = "rgba(239, 68, 68, 0.14)"
        red_border = "rgba(239, 68, 68, 0.45)"
        amber_bg = "rgba(245, 158, 11, 0.15)"
        amber_border = "rgba(245, 158, 11, 0.42)"
        shadow_card = "0 14px 34px -10px rgba(0, 0, 0, 0.55)"
        app_bg_css = """
            radial-gradient(circle at 85% 15%, rgba(139, 92, 246, 0.18) 0%, transparent 45%),
            radial-gradient(circle at 15% 85%, rgba(236, 72, 153, 0.10) 0%, transparent 50%),
            #0F1226
        """
    else:
        bg_app = "#F4F7FF"
        bg_sidebar = "#FFFFFF"
        bg_card = "#FFFFFF"
        bg_card_2 = "#F8FAFF"
        border_col = "#E2E8F0"
        text_main = "#0B1938"
        text_muted = "#64748B"
        accent = "#6328E8"
        accent_soft = "#EDE9FE"
        red_bg = "#FEF2F2"
        red_border = "#FECACA"
        amber_bg = "#FEF3C7"
        amber_border = "#FDE68A"
        shadow_card = "0 16px 36px -14px rgba(99, 40, 232, 0.14)"
        app_bg_css = """
            radial-gradient(circle at 85% 20%, rgba(167, 139, 250, 0.22) 0%, transparent 45%),
            radial-gradient(circle at 15% 85%, rgba(191, 219, 254, 0.35) 0%, transparent 50%),
            linear-gradient(135deg, #F5F8FF 0%, #EDF2FF 55%, #E8EEFF 100%)
        """

    st.html(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {{
            --bg-app: {bg_app};
            --bg-sidebar: {bg_sidebar};
            --bg-card: {bg_card};
            --bg-card-2: {bg_card_2};
            --border-col: {border_col};
            --text-main: {text_main};
            --text-muted: {text_muted};
            --accent: {accent};
            --accent-soft: {accent_soft};
            --red-bg: {red_bg};
            --red-border: {red_border};
            --amber-bg: {amber_bg};
            --amber-border: {amber_border};
        }}

        [data-testid="InputInstructions"] {{
            display: none !important;
        }}

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--text-main);
        }}

        .stApp {{
            background: {app_bg_css};
        }}

        section[data-testid="stSidebar"] {{
            background-color: var(--bg-sidebar) !important;
            border-right: 1px solid var(--border-col) !important;
        }}

        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}

        .block-container {{
            padding-top: 1.2rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 1420px !important;
            perspective: 1400px;
        }}

        /* ================= KEYFRAMES ĐỘNG & 3D ================= */
        @keyframes slideUp3D {{
            from {{ opacity: 0; transform: perspective(1000px) translateY(16px) rotateX(-5deg); }}
            to {{ opacity: 1; transform: perspective(1000px) translateY(0) rotateX(0deg); }}
        }}
        @keyframes float3D {{
            0%, 100% {{ transform: translate3d(0, 0px, 0) rotateY(-3deg); }}
            50% {{ transform: translate3d(0, -7px, 14px) rotateY(3deg); }}
        }}
        @keyframes pulsePurple {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(99, 40, 232, 0.40); }}
            50% {{ box-shadow: 0 0 0 7px rgba(99, 40, 232, 0); }}
        }}
        @keyframes pulseDanger {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.35); }}
            50% {{ box-shadow: 0 0 0 7px rgba(239, 68, 68, 0); }}
        }}
        @keyframes shimmerBar {{
            0% {{ background-position: -200% 0; }}
            100% {{ background-position: 200% 0; }}
        }}

        /* ================= STATUS STRIP & CARDS 3D ================= */
        .account-strip {{
            background: linear-gradient(90deg, var(--accent-soft) 0%, var(--bg-card) 100%);
            border: 1px solid rgba(99, 40, 232, 0.35);
            border-radius: 16px;
            padding: 12px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 16px;
            box-shadow: 0 8px 24px -10px rgba(99, 40, 232, 0.18);
            animation: slideUp3D 0.45s ease-out;
        }}

        .kpi-3d-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-col);
            border-radius: 20px;
            padding: 18px 20px;
            box-shadow: {shadow_card};
            transform-style: preserve-3d;
            transition: transform 0.18s ease-out, box-shadow 0.22s ease, border-color 0.22s ease;
            position: relative;
            overflow: hidden;
            animation: slideUp3D 0.5s ease-out;
        }}
        .kpi-3d-card:hover {{
            border-color: var(--accent);
            box-shadow: 0 22px 40px -12px rgba(99, 40, 232, 0.22);
        }}
        .kpi-3d-card.danger-border {{
            border-color: var(--red-border);
        }}

        .glass-panel {{
            background: var(--bg-card);
            border: 1px solid var(--border-col);
            border-radius: 22px;
            padding: 20px 22px;
            box-shadow: {shadow_card};
            margin-bottom: 14px;
            animation: slideUp3D 0.55s ease-out;
        }}

        .summary-chi-box {{
            background: var(--red-bg);
            border: 1px solid var(--red-border);
            border-radius: 16px;
            padding: 14px 18px;
            transform-style: preserve-3d;
            transition: transform 0.2s ease;
        }}
        .summary-thu-box {{
            background: var(--accent-soft);
            border: 1px solid rgba(99, 40, 232, 0.35);
            border-radius: 16px;
            padding: 14px 18px;
            transform-style: preserve-3d;
            transition: transform 0.2s ease;
        }}

        /* ================= LỊCH TÀI CHÍNH 3D (CALENDAR CELLS) ================= */
        .cal-header-row {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
            text-align: center;
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
            margin: 10px 0 8px 0;
        }}
        .cal-grid {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
        }}
        .cal-cell {{
            border-radius: 14px;
            padding: 8px 6px;
            min-height: 64px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--border-col);
            background: var(--bg-card-2);
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease;
            transform-style: preserve-3d;
        }}
        .cal-cell:hover {{
            transform: perspective(600px) translateY(-4px) scale(1.04) rotateX(4deg);
            box-shadow: 0 12px 24px -6px rgba(99, 40, 232, 0.22);
            border-color: var(--accent);
        }}
        .cal-cell.high-spend {{
            background: var(--red-bg);
            border-color: var(--red-border);
        }}
        .cal-cell.mid-spend {{
            background: var(--amber-bg);
            border-color: var(--amber-border);
        }}
        .cal-cell.today-cell {{
            border: 2px solid var(--accent);
            animation: pulsePurple 2.4s infinite;
        }}
        .cal-cell.empty-cell {{
            background: transparent;
            border-color: transparent;
        }}
        .cal-day-num {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-main);
        }}
        .cal-day-amt {{
            font-size: 11px;
            font-weight: 700;
            margin-top: 3px;
        }}

        /* ================= THANH TIẾN ĐỘ & CẢNH BÁO ================= */
        .progress-track {{
            width: 100%;
            height: 10px;
            background: #EDE9FE;
            border-radius: 999px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill-shimmer {{
            height: 100%;
            border-radius: 999px;
            background-size: 200% 100%;
            animation: shimmerBar 2.8s linear infinite;
        }}
        .alert-row-red {{
            background: var(--red-bg);
            border: 1px solid var(--red-border);
            border-radius: 14px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 13.5px;
            font-weight: 600;
            color: #DC2626;
            animation: pulseDanger 2.5s infinite;
        }}

        /* ================= NÚT BẤM TÍM PHÁT SÁNG ================= */
        div.stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #6328E8 0%, #7C3AED 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            box-shadow: 0 8px 22px -6px rgba(99, 40, 232, 0.50) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        }}
        div.stButton > button[kind="primary"]:hover {{
            transform: translateY(-2px) scale(1.01) !important;
            box-shadow: 0 12px 26px -6px rgba(99, 40, 232, 0.65) !important;
        }}

        .float-3d-img {{
            animation: float3D 4.8s ease-in-out infinite;
            filter: drop-shadow(0 18px 28px rgba(99, 40, 232, 0.24));
        }}
    </style>
    """)

    # JavaScript 3D Tilt + Spotlight Glare tím-hồng theo con trỏ chuột
    components.html("""
    <script>
    (function() {
        const doc = window.parent.document;
        function bind3D() {
            const cards = doc.querySelectorAll('.kpi-3d-card, .summary-chi-box, .summary-thu-box');
            cards.forEach(card => {
                if (card.dataset.tilt3d === "1") return;
                card.dataset.tilt3d = "1";
                const glare = doc.createElement('div');
                glare.style.cssText = 'position:absolute;inset:0;pointer-events:none;border-radius:inherit;opacity:0;transition:opacity 0.2s ease;z-index:2;';
                card.appendChild(glare);
                card.addEventListener('mousemove', (e) => {
                    const r = card.getBoundingClientRect();
                    const x = e.clientX - r.left;
                    const y = e.clientY - r.top;
                    const rx = (((y - r.height / 2) / (r.height / 2))) * -7;
                    const ry = (((x - r.width / 2) / (r.width / 2))) * 7;
                    card.style.transform = `perspective(900px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) translateY(-4px) scale3d(1.015,1.015,1.015)`;
                    glare.style.opacity = '1';
                    glare.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(99,40,232,0.16) 0%, transparent 65%)`;
                });
                card.addEventListener('mouseleave', () => {
                    card.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) translateY(0px) scale3d(1,1,1)';
                    glare.style.opacity = '0';
                });
            });
        }
        bind3D();
        setInterval(bind3D, 750);
    })();
    </script>
    """, height=0, width=0)


def sparkline_svg(color: str, trend_up: bool = True) -> str:
    """Tạo đường sparkline SVG mượt ở góc dưới thẻ KPI giống mẫu thuvien01."""
    path = "M 2 24 Q 25 22, 45 14 T 88 4" if trend_up else "M 2 18 Q 28 22, 48 16 T 88 12"
    return f"""
    <svg width="86" height="28" viewBox="0 0 90 28" fill="none">
        <path d="{path}" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>
    </svg>
    """


# =============================================================================
# 3. KẾT NỐI BACKEND & KHỞI TẠO TRẠNG THÁI GIAO DIỆN
# =============================================================================
@st.cache_resource
def get_backend(path: str) -> ExpenseBackend:
    return ExpenseBackend(path)


backend = get_backend(str(database_path()))
available_months = backend.get_available_months()

if "is_dark" not in st.session_state:
    st.session_state.is_dark = False
if st.session_state.get("selected_month") not in available_months:
    st.session_state.selected_month = available_months[0]
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Lịch tài chính"
if "selected_day" not in st.session_state:
    st.session_state.selected_day = date.today().strftime("%Y-%m-%d")

inject_emerald_3d_theme(st.session_state.is_dark)

selected_month = st.session_state.selected_month
y_int, m_int = map(int, selected_month.split("-"))

# Lấy dữ liệu thật từ Backend
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

days_in_month = calendar.monthrange(y_int, m_int)[1]
today_obj = date.today()
if y_int == today_obj.year and m_int == today_obj.month:
    days_left = max(1, days_in_month - today_obj.day + 1)
else:
    days_left = days_in_month
safe_daily = max(0.0, budget_remaining) / days_left


# =============================================================================
# 4. SIDEBAR BÊN TRÁI (GIỐNG MẪU THUVIEN01)
# =============================================================================
with st.sidebar:
    st.html("""
    <div style="display:flex; align-items:center; gap:12px; padding:6px 4px 16px 4px; border-bottom:1px solid var(--border-col); margin-bottom:14px;">
        <div style="width:44px; height:44px; border-radius:12px; background:var(--accent-soft); border:1px solid var(--accent); display:flex; align-items:center; justify-content:center; font-size:22px;">🐷</div>
        <div>
            <div style="font-size:18px; font-weight:800; color:var(--text-main);">UTH Spend</div>
            <div style="font-size:11.5px; color:var(--text-muted);">Quản lý chi tiêu sinh viên</div>
        </div>
    </div>
    <div style="font-size:11px; font-weight:700; letter-spacing:0.06em; color:var(--text-muted); margin-bottom:8px;">ĐIỀU HƯỚNG CHÍNH</div>
    """)

    nav_options = [
        "Lịch tài chính",
        "Thống kê chi tiêu",
        "Nhập Thu / Chi & CSV",
        "Cảnh báo & Ngân sách",
    ]
    nav_icons = {
        "Lịch tài chính": "📅",
        "Thống kê chi tiêu": "📊",
        "Nhập Thu / Chi & CSV": "💳",
        "Cảnh báo & Ngân sách": "🚨",
    }
    st.radio(
        "Điều hướng",
        options=nav_options,
        key="nav_page",
        format_func=lambda x: f"{nav_icons[x]}  {x}",
        label_visibility="collapsed"
    )

    st.markdown("---")
    # Hộp Gợi ý thông minh ở Sidebar
    tip_color = "#10B981" if budget_remaining >= 0 else "#F87171"
    tip_text = (
        f"Có thể chi an toàn <strong>{format_vnd(safe_daily)}/ngày</strong> trong {days_left} ngày tới."
        if budget_remaining >= 0
        else f"Đã vượt định mức tháng <strong>{format_vnd(abs(budget_remaining))}</strong>. Hạn chế chi không thiết yếu!"
    )
    st.html(f"""
    <div style="background:var(--accent-soft); border:1px solid var(--accent); border-radius:14px; padding:14px; margin-bottom:14px;">
        <div style="font-size:12.5px; font-weight:700; color:var(--accent); margin-bottom:6px;">✨ Gợi ý từ UTH AI</div>
        <div style="font-size:12.5px; color:var(--text-main); line-height:1.45;">{tip_text}</div>
    </div>
    """)

    theme_btn_label = "☀️ Chuyển Light Mode" if st.session_state.is_dark else "🌙 Chuyển Dark Mode"
    if st.button(theme_btn_label, use_container_width=True):
        st.session_state.is_dark = not st.session_state.is_dark
        st.rerun()

    st.caption(f"Tháng {selected_month} · SQLite3 Backend ({len(df_month)} GD)")


# =============================================================================
# 5. TOP HEADER BAR & THANH TRẠNG THÁI TÀI KHOẢN
# =============================================================================
h_left, h_m_prev, h_m_lbl, h_m_next, h_today, h_quick = st.columns([3.2, 0.45, 1.3, 0.45, 0.85, 1.15])

with h_left:
    page_titles = {
        "Lịch tài chính": ("Tổng quan tài chính", "Sinh viên UTH · Theo dõi chi tiêu hằng ngày thông minh hơn nhé!"),
        "Thống kê chi tiêu": ("Thống kê chi tiêu", "Phân tích Tiền ăn, Tiền trọ, Đi lại, tỷ trọng danh mục & biểu đồ theo tháng."),
        "Nhập Thu / Chi & CSV": ("Sổ Thu Chi & Nhập/Xuất CSV", "Ghi nhanh khoản thu chi hằng ngày, lọc dữ liệu và xuất/nhập file CSV."),
        "Cảnh báo & Ngân sách": ("Cảnh báo & Thiết lập Ngân sách", "Kiểm soát định mức tháng, giả lập chi tiêu và nhận cảnh báo vượt ngưỡng."),
    }
    p_title, p_sub = page_titles[st.session_state.nav_page]
    st.html(f"""
    <div style="font-size:30px; font-weight:800; letter-spacing:-0.02em; color:var(--text-main);">{p_title}</div>
    <div style="font-size:13.5px; color:var(--text-muted); margin-top:2px;">{p_sub}</div>
    """)

idx_m = available_months.index(selected_month)
with h_m_prev:
    st.write("")
    if st.button("‹", use_container_width=True, help="Tháng trước"):
        if idx_m + 1 < len(available_months):
            st.session_state.selected_month = available_months[idx_m + 1]
            st.rerun()
with h_m_lbl:
    st.write("")
    st.html(f'<div style="text-align:center; padding:8px 10px; border-radius:10px; border:1px solid var(--border-col); background:var(--bg-card); font-weight:700; font-size:13.5px;">Tháng {m_int:02d}, {y_int}</div>')
with h_m_next:
    st.write("")
    if st.button("›", use_container_width=True, help="Tháng sau"):
        if idx_m - 1 >= 0:
            st.session_state.selected_month = available_months[idx_m - 1]
            st.rerun()
with h_today:
    st.write("")
    if st.button("Hôm nay", use_container_width=True):
        st.session_state.selected_month = available_months[0]
        st.session_state.selected_day = date.today().strftime("%Y-%m-%d")
        st.rerun()
with h_quick:
    st.write("")
    st.button(
        "➕ Ghi nhanh",
        type="primary",
        use_container_width=True,
        on_click=lambda: st.session_state.update(nav_page="Nhập Thu / Chi & CSV"),
    )

# Thanh trạng thái tài khoản màu xanh ngọc giống mẫu thuvien01
st.html(f"""
<div class="account-strip">
    <div style="font-size:13.5px; font-weight:600; color:var(--text-main);">
        👤 Tài khoản: <span style="color:var(--accent); font-weight:700;">Sinh viên UTH</span>
        <span style="color:var(--text-muted); font-weight:500;"> · {len(df_month)} giao dịch · Tháng {selected_month}</span>
    </div>
    <div style="font-size:12px; font-weight:700; color:var(--accent); background:var(--accent-soft); padding:5px 12px; border-radius:99px; border:1px solid var(--accent);">
        ⚡ Kết nối Backend Python trực tiếp
    </div>
</div>
""")


# =============================================================================
# 6. 4 THẺ KPI VỚI SPARKLINE MINI & HIỆU ỨNG NGHIÊNG 3D
# =============================================================================
k1, k2, k3, k4 = st.columns(4)
bal_color = "#6328E8" if balance >= 0 else "#DC2626"

with k1:
    st.html(f"""
    <div class="kpi-3d-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-size:13px; color:var(--text-muted); font-weight:600;">Số dư khả dụng</span>
            <span style="width:32px; height:32px; border-radius:9px; background:var(--accent-soft); color:var(--accent); display:flex; align-items:center; justify-content:center;">💳</span>
        </div>
        <div style="font-size:24px; font-weight:800; color:{bal_color}; margin-bottom:8px;">{format_vnd(balance)}</div>
        <div style="display:flex; justify-content:space-between; align-items:flex-end;">
            <span style="font-size:12px; color:var(--text-muted);">Tháng {selected_month}</span>
            {sparkline_svg("#6328E8", trend_up=(balance >= 0))}
        </div>
    </div>
    """)

with k2:
    st.html(f"""
    <div class="kpi-3d-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-size:13px; color:var(--text-muted); font-weight:600;">Tổng thu nhập</span>
            <span style="width:32px; height:32px; border-radius:9px; background:var(--accent-soft); color:var(--accent); display:flex; align-items:center; justify-content:center;">↙</span>
        </div>
        <div style="font-size:24px; font-weight:800; color:#16A34A; margin-bottom:8px;">+{format_vnd(total_income)}</div>
        <div style="display:flex; justify-content:space-between; align-items:flex-end;">
            <span style="font-size:12px; color:var(--text-muted);">Nguồn thu trong tháng</span>
            {sparkline_svg("#16A34A", trend_up=True)}
        </div>
    </div>
    """)

with k3:
    tx_exp_cnt = len(df_month[df_month["tx_type"] == "Chi tiêu"]) if not df_month.empty else 0
    st.html(f"""
    <div class="kpi-3d-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-size:13px; color:var(--text-muted); font-weight:600;">Tổng chi tiêu</span>
            <span style="width:32px; height:32px; border-radius:9px; background:var(--red-bg); color:#DC2626; display:flex; align-items:center; justify-content:center;">↗</span>
        </div>
        <div style="font-size:24px; font-weight:800; color:#DC2626; margin-bottom:8px;">-{format_vnd(total_expense)}</div>
        <div style="display:flex; justify-content:space-between; align-items:flex-end;">
            <span style="font-size:12px; color:var(--text-muted);">{tx_exp_cnt} giao dịch đã ghi</span>
            {sparkline_svg("#DC2626", trend_up=False)}
        </div>
    </div>
    """)

with k4:
    is_over = budget_remaining < 0
    k4_cls = "kpi-3d-card danger-border" if is_over else "kpi-3d-card"
    k4_sub = f"Vượt {format_vnd(abs(budget_remaining))}" if is_over else f"Còn {format_vnd(budget_remaining)}"
    k4_sub_col = "#F87171" if is_over else "#10B981"
    st.html(f"""
    <div class="{k4_cls}">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-size:13px; color:var(--text-muted); font-weight:600;">Có thể chi hôm nay</span>
            <span style="width:32px; height:32px; border-radius:9px; background:{'var(--red-bg)' if is_over else 'var(--accent-soft)'}; color:{k4_sub_col}; display:flex; align-items:center; justify-content:center;">{'⚠️' if is_over else '🛡️'}</span>
        </div>
        <div style="font-size:24px; font-weight:800; color:var(--text-main); margin-bottom:8px;">{format_vnd(safe_daily)}</div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; font-weight:700; color:{k4_sub_col};">
            <span>{k4_sub}</span>
            <span>{budget_used_pct:.1f}%</span>
        </div>
    </div>
    """)

st.write("")


# =============================================================================
# TRANG 1: LỊCH TÀI CHÍNH (MONEY CALENDAR + CẢNH BÁO + GIAO DỊCH GẦN ĐÂY)
# =============================================================================
if st.session_state.nav_page == "Lịch tài chính":
    cal_left, cal_right = st.columns([1.85, 1.0], gap="large")

    # Tính chi tiêu theo từng ngày trong tháng
    daily_exp_map = {}
    if not df_month.empty:
        df_exp_m = df_month[df_month["tx_type"] == "Chi tiêu"]
        daily_exp_map = df_exp_m.groupby("date")["amount"].sum().to_dict()

    with cal_left:
        st.html(f"""
        <div style="font-size:13px; font-weight:800; letter-spacing:0.06em; color:var(--text-muted); margin-bottom:10px;">
            🔥 LỊCH TÀI CHÍNH — THÁNG {m_int:02d}/{y_int}
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
            <div class="summary-chi-box">
                <div style="font-size:11.5px; font-weight:700; color:#DC2626;">↗ CHI THÁNG NÀY</div>
                <div style="font-size:24px; font-weight:800; color:#DC2626; margin-top:4px;">{format_vnd(total_expense)}</div>
            </div>
            <div class="summary-thu-box">
                <div style="font-size:11.5px; font-weight:700; color:#6328E8;">↙ THU THÁNG NÀY</div>
                <div style="font-size:24px; font-weight:800; color:#6328E8; margin-top:4px;">+{format_vnd(total_income)}</div>
            </div>
        </div>
        """)

        # Lưới Lịch 7 cột (T2 - CN)
        first_wd, num_days = calendar.monthrange(y_int, m_int)  # Monday=0..Sunday=6
        cells_html = ""
        for _ in range(first_wd):
            cells_html += '<div class="cal-cell empty-cell"></div>'

        for d_num in range(1, num_days + 1):
            d_key = f"{y_int:04d}-{m_int:02d}-{d_num:02d}"
            spent_d = float(daily_exp_map.get(d_key, 0.0))
            is_today = (d_key == date.today().strftime("%Y-%m-%d"))

            cls_list = ["cal-cell"]
            if spent_d >= 500_000:
                cls_list.append("high-spend")
                amt_color = "#DC2626"
            elif spent_d > 0:
                cls_list.append("mid-spend")
                amt_color = "#D97706"
            else:
                amt_color = "var(--text-muted)"

            if is_today:
                cls_list.append("today-cell")

            amt_str = format_compact_vnd(spent_d) if spent_d > 0 else "—"
            cells_html += f"""
            <div class="{' '.join(cls_list)}">
                <div class="cal-day-num">{d_num}</div>
                <div class="cal-day-amt" style="color:{amt_color};">{amt_str}</div>
            </div>
            """

        st.html(f"""
        <div class="glass-panel">
            <div class="cal-header-row">
                <div>T2</div><div>T3</div><div>T4</div><div>T5</div><div>T6</div><div>T7</div><div>CN</div>
            </div>
            <div class="cal-grid">
                {cells_html}
            </div>
        </div>
        """)

        # Hộp Chi tiêu an toàn & Báo cáo cảnh báo vượt định mức (ngay dưới Lịch)
        pct_bar = min(budget_used_pct, 100.0)
        bar_grad = (
            "linear-gradient(90deg, #EF4444, #F87171, #EF4444)"
            if budget_used_pct > 100
            else ("linear-gradient(90deg, #F59E0B, #FBBF24, #F59E0B)" if budget_used_pct >= 80 else "linear-gradient(90deg, #10B981, #34D399, #10B981)")
        )
        status_pill = (
            f"Vượt định mức (+{budget_used_pct - 100:.1f}%)"
            if budget_used_pct > 100
            else ("Sắp chạm ngưỡng" if budget_used_pct >= 80 else "Trong vùng an toàn")
        )
        status_col = "#F87171" if budget_used_pct > 100 else ("#FBBF24" if budget_used_pct >= 80 else "#10B981")

        danger_list_html = ""
        for a in alerts:
            if a["level"] in ("danger", "warning"):
                c_tag = "#F87171" if a["level"] == "danger" else "#FBBF24"
                danger_list_html += f'<div style="font-size:12.5px; color:{c_tag}; margin-top:5px;">• {a["message"]}</div>'
        if not danger_list_html:
            danger_list_html = '<div style="font-size:12.5px; color:#10B981; margin-top:5px;">• Tất cả hạng mục đều đang nằm trong định mức cho phép.</div>'

        st.html(f"""
        <div class="glass-panel" style="border-color:{status_col};">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:15px; font-weight:700;">🛡️ Chi tiêu an toàn</span>
                <span style="font-size:11.5px; font-weight:700; padding:4px 10px; border-radius:99px; background:var(--red-bg); color:{status_col};">{status_pill}</span>
            </div>
            <div style="font-size:26px; font-weight:800; color:var(--text-main);">{format_vnd(safe_daily)} <span style="font-size:14px; color:var(--text-muted); font-weight:500;">/ ngày</span></div>
            <div class="progress-track">
                <div class="progress-fill-shimmer" style="width:{pct_bar:.1f}%; background-image:{bar_grad};"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-muted); margin-bottom:10px;">
                <span>Đã chi tháng này: <strong>{format_vnd(total_expense)}</strong></span>
                <span>Định mức: <strong>{format_vnd(total_budget)} ({budget_used_pct:.1f}%)</strong></span>
            </div>
            <div style="background:var(--bg-card-2); border:1px solid var(--border-col); border-radius:12px; padding:12px 14px;">
                <div style="font-size:11.5px; font-weight:700; letter-spacing:0.04em; color:{status_col};">BÁO CÁO CẢNH BÁO NGÂN SÁCH</div>
                {danger_list_html}
            </div>
        </div>
        """)

    with cal_right:
        # Thẻ Gợi ý từ UTH AI + ảnh 3D nổi bên phải
        wallet_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "wallet_3d.jpg")
        img_tag = ""
        if os.path.exists(wallet_img_path):
            with open(wallet_img_path, "rb") as f_img:
                b64_img = base64.b64encode(f_img.read()).decode("utf-8")
            img_tag = f'<img src="data:image/jpeg;base64,{b64_img}" class="float-3d-img" style="width:92px; height:92px; border-radius:16px; object-fit:cover;" />'

        st.html(f"""
        <div class="glass-panel" style="background:linear-gradient(135deg, var(--accent-soft) 0%, var(--bg-card) 100%); border-color:var(--accent);">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
                <div>
                    <div style="font-size:13px; font-weight:700; color:var(--accent); margin-bottom:6px;">✨ Gợi ý từ UTH AI</div>
                    <div style="font-size:13.5px; color:var(--text-main); line-height:1.45;">
                        {tip_text}
                    </div>
                </div>
                {img_tag}
            </div>
        </div>
        """)

        # Chọn ngày xem chi tiết ngay trên cột phải
        picked_day = st.date_input("📅 Xem giao dịch theo ngày:", value=datetime.strptime(st.session_state.selected_day, "%Y-%m-%d").date())
        picked_str = picked_day.strftime("%Y-%m-%d")
        st.session_state.selected_day = picked_str
        df_day = df_month[df_month["date"] == picked_str] if not df_month.empty else pd.DataFrame()
        day_total = float(df_day[df_day["tx_type"] == "Chi tiêu"]["amount"].sum()) if not df_day.empty else 0.0

        day_rows_html = ""
        if not df_day.empty:
            for _, r in df_day.iterrows():
                col_r = "#F87171" if r["tx_type"] == "Chi tiêu" else "#10B981"
                sign_r = "-" if r["tx_type"] == "Chi tiêu" else "+"
                day_rows_html += f"""
                <div style="display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid var(--border-col); font-size:13px;">
                    <span>{escape(str(r["category"]))} · <span style="color:var(--text-muted);">{escape(str(r["note"]))}</span></span>
                    <strong style="color:{col_r};">{sign_r}{format_vnd(r['amount'])}</strong>
                </div>
                """
        else:
            day_rows_html = '<div style="font-size:13px; color:var(--text-muted); padding:6px 0;">Chưa có giao dịch trong ngày này. Mở mục Ghi nhanh bên dưới để thêm.</div>'

        st.html(f"""
        <div class="glass-panel">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:14px; font-weight:700; color:var(--accent);">📅 Ngày {picked_day.strftime('%d/%m/%Y')}</span>
                <span style="font-size:14px; font-weight:800;">{format_vnd(day_total)}</span>
            </div>
            {day_rows_html}
        </div>
        """)

        # Giao dịch gần đây
        recent_html = ""
        if not df_month.empty:
            for _, r in df_month.head(6).iterrows():
                is_exp = r["tx_type"] == "Chi tiêu"
                amt_c = "#F87171" if is_exp else "#10B981"
                sgn = "-" if is_exp else "+"
                d_fmt = datetime.strptime(r["date"], "%Y-%m-%d").strftime("%d/%m")
                recent_html += f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:1px solid var(--border-col);">
                    <div>
                        <div style="font-size:13.5px; font-weight:600; color:var(--text-main);">{escape(str(r["note"]))}</div>
                        <div style="font-size:11.5px; color:var(--text-muted);">{d_fmt} · {escape(str(r["category"]))}</div>
                    </div>
                    <div style="font-size:13.5px; font-weight:700; color:{amt_c}; white-space:nowrap;">{sgn}{format_vnd(r['amount'])}</div>
                </div>
                """
        else:
            recent_html = '<div style="font-size:13px; color:var(--text-muted);">Chưa có giao dịch nào.</div>'

        st.html(f"""
        <div class="glass-panel">
            <div style="font-size:14px; font-weight:700; margin-bottom:6px;">🕒 Giao dịch gần đây</div>
            {recent_html}
        </div>
        """)

    # Quick Add Expander dưới cùng
    with st.expander(f"⚡ Quick Add — Ghi nhanh ngày {picked_day.strftime('%d/%m/%Y')}", expanded=False):
        qa_c1, qa_c2, qa_c3, qa_c4, qa_c5 = st.columns([1, 1.2, 1.1, 1.6, 1])
        with qa_c1:
            qa_type = st.selectbox("Loại:", ["Chi tiêu", "Thu nhập"], key="qa_type")
        with qa_c2:
            qa_cats = backend.get_categories(qa_type)
            qa_cat = st.selectbox("Danh mục:", list(qa_cats.keys()), format_func=lambda c: f"{qa_cats[c]['icon']} {c}", key="qa_cat")
        with qa_c3:
            qa_amt = st.number_input("Số tiền (đ):", min_value=0, max_value=500_000_000, value=35_000, step=5_000, key="qa_amt")
        with qa_c4:
            qa_note = st.text_input("Ghi chú:", placeholder="VD: Cơm trưa, Đổ xăng...", key="qa_note")
        with qa_c5:
            st.write("")
            if st.button("💾 Lưu ngay", type="primary", use_container_width=True, key="qa_btn"):
                ok, msg = backend.add_daily_transaction(picked_str, qa_type, qa_cat, float(qa_amt), qa_note)
                if ok:
                    st.toast(f"✅ {msg}", icon="💚")
                    st.rerun()
                else:
                    st.error(msg)


# =============================================================================
# TRANG 2: THỐNG KÊ CHI TIÊU (TIỀN ĂN • TIỀN TRỌ • ĐI LẠI & BIỂU ĐỒ)
# =============================================================================
elif st.session_state.nav_page == "Thống kê chi tiêu":
    # Banner cảnh báo vượt ngân sách đỏ
    for a in alerts:
        if a["level"] == "danger":
            st.html(f"""
            <div class="alert-row-red">
                <span>⚠️ {a['message']}</span>
                <span style="font-size:11.5px; background:rgba(239,68,68,0.2); padding:3px 10px; border-radius:99px;">Vượt ngân sách</span>
            </div>
            """)

    st.html('<div style="font-size:18px; font-weight:800; margin:14px 0 10px 0;">🍜 Theo dõi 3 khoản chi thiết yếu: Tiền ăn • Tiền trọ • Đi lại</div>')
    e_cols = st.columns(3, gap="medium")
    for idx, item in enumerate(essential_stats):
        pct_b = min(item["percent"], 100.0)
        b_col = "#EF4444" if item["status"] == "danger" else ("#F59E0B" if item["status"] == "warning" else "#10B981")
        with e_cols[idx]:
            st.html(f"""
            <div class="kpi-3d-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:16px; font-weight:700;">{item['icon']} {item['category']}</span>
                    <span style="font-size:12px; font-weight:700; color:{b_col};">{item['percent']:.1f}%</span>
                </div>
                <div style="font-size:24px; font-weight:800; color:{b_col};">{format_vnd(item['spent'])}</div>
                <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">Định mức: {format_vnd(item['limit'])} · Tỷ trọng {item['share_of_total']:.1f}%</div>
                <div class="progress-track">
                    <div class="progress-fill-shimmer" style="width:{pct_b:.1f}%; background:{b_col};"></div>
                </div>
                <div style="font-size:12.5px; font-weight:600; color:var(--text-main);">{item['note_text']}</div>
            </div>
            """)

    st.write("")
    c1, c2 = st.columns(2, gap="medium")
    df_pie = charts_data["pie_month"]
    df_monthly_io = charts_data["monthly_io"]
    df_core3 = charts_data["core3_trend"]
    df_daily = charts_data["daily_expense"]

    with c1:
        if not df_pie.empty:
            donut = (
                alt.Chart(df_pie)
                .mark_arc(innerRadius=60, outerRadius=110, cornerRadius=6)
                .encode(
                    theta=alt.Theta("amount:Q"),
                    color=alt.Color("category:N", title="Danh mục", scale=alt.Scale(scheme="tableau10")),
                    tooltip=[alt.Tooltip("category:N"), alt.Tooltip("amount:Q", format=",.0f"), alt.Tooltip("pct:Q", format=".1f")]
                )
                .properties(height=310, title=f"Cơ cấu chi tiêu tháng {selected_month}")
            )
            st.altair_chart(donut, use_container_width=True)

    with c2:
        if not df_monthly_io.empty:
            bar_io = (
                alt.Chart(df_monthly_io)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=26)
                .encode(
                    x=alt.X("month:N", title="Tháng", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("amount:Q", title="Số tiền (VNĐ)"),
                    xOffset="tx_type:N",
                    color=alt.Color("tx_type:N", title="Loại", scale=alt.Scale(domain=["Thu nhập", "Chi tiêu"], range=["#10B981", "#EF4444"])),
                    tooltip=[alt.Tooltip("month:N"), alt.Tooltip("tx_type:N"), alt.Tooltip("amount:Q", format=",.0f")]
                )
                .properties(height=310, title="Xu hướng Thu Nhập vs Chi Tiêu theo Tháng")
            )
            st.altair_chart(bar_io, use_container_width=True)

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        if not df_core3.empty:
            line_c3 = (
                alt.Chart(df_core3)
                .mark_line(point=alt.OverlayMarkDef(size=90, filled=True), strokeWidth=3, interpolate="monotone")
                .encode(
                    x=alt.X("month:N", title="Tháng", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("amount:Q", title="VNĐ"),
                    color=alt.Color("category:N", title="Nhóm chính", scale=alt.Scale(domain=["Tiền ăn", "Tiền trọ", "Đi lại"], range=["#EF4444", "#10B981", "#38BDF8"])),
                    tooltip=[alt.Tooltip("month:N"), alt.Tooltip("category:N"), alt.Tooltip("amount:Q", format=",.0f")]
                )
                .properties(height=270, title="Biến động Tiền ăn • Tiền trọ • Đi lại qua các tháng")
            )
            st.altair_chart(line_c3, use_container_width=True)

    with c4:
        if not df_daily.empty:
            area_d = (
                alt.Chart(df_daily)
                .mark_area(
                    interpolate="monotone",
                    line={"color": "#10B981", "strokeWidth": 2.5},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[alt.GradientStop(color="rgba(16,185,129,0.45)", offset=0), alt.GradientStop(color="rgba(16,185,129,0.02)", offset=1)],
                        x1=1, x2=1, y1=1, y2=0,
                    ),
                    point=alt.OverlayMarkDef(color="#10B981", size=60)
                )
                .encode(
                    x=alt.X("date:N", title="Ngày", axis=alt.Axis(labelAngle=-30)),
                    y=alt.Y("amount:Q", title="VNĐ"),
                    tooltip=[alt.Tooltip("date:N"), alt.Tooltip("amount:Q", format=",.0f")]
                )
                .properties(height=270, title=f"Chi tiêu hằng ngày trong tháng {selected_month}")
            )
            st.altair_chart(area_d, use_container_width=True)

    st.markdown(f"#### 📋 Bảng tỷ trọng hạng mục chi tiêu tháng {selected_month}")
    st.dataframe(
        df_category_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Đã chi (VNĐ)": st.column_config.NumberColumn(format="%d đ"),
            "Định mức (VNĐ)": st.column_config.NumberColumn(format="%d đ"),
            "Tỷ lệ dùng (%)": st.column_config.ProgressColumn("Tiến độ (%)", format="%.1f%%", min_value=0, max_value=120),
            "Tỷ trọng (%)": st.column_config.NumberColumn(format="%.1f%%"),
        }
    )


# =============================================================================
# TRANG 3: NHẬP THU / CHI & XUẤT / NHẬP CSV RÕ RÀNG
# =============================================================================
elif st.session_state.nav_page == "Nhập Thu / Chi & CSV":
    with st.expander("Nhập giao dịch từ CSV", icon=":material/upload_file:"):
        st.caption(
            "Chọn tệp CSV UTF-8 có các cột Ngày, Loại, Danh mục, Số tiền (VNĐ) "
            "và Ghi chú (tùy chọn). Bạn cũng có thể dùng tệp CSV đã xuất từ UniSpend."
        )
        upload_id = st.session_state.get("transaction_csv_upload_id", 0)
        uploaded_csv = st.file_uploader("Chọn tệp CSV", type=["csv"], key=f"import_csv_uploader_{upload_id}")
        if uploaded_csv is not None:
            try:
                transactions = read_transactions_csv(uploaded_csv.getvalue())
            except (ValueError, CsvError) as exc:
                st.error(f"Không đọc được file CSV: {exc}")
            else:
                if not transactions:
                    st.info("Tệp CSV chưa có giao dịch.")
                else:
                    st.info(f"Tìm thấy **{len(transactions)}** giao dịch hợp lệ.")
                    st.caption("Xem trước tối đa 5 giao dịch")
                    st.dataframe(
                        [
                            {
                                "Ngày": tx.date,
                                "Loại": tx.tx_type,
                                "Danh mục": tx.category,
                                "Số tiền": format_vnd(tx.amount),
                                "Ghi chú": tx.note,
                            }
                            for tx in transactions[:5]
                        ],
                        hide_index=True,
                        width="stretch",
                    )
                    if st.button("✅ Xác nhận nhập vào sổ", type="primary"):
                        try:
                            backend.db.insert_transactions(transactions)
                        except DatabaseError:
                            st.error("Chưa lưu được giao dịch. Hãy thử lại.")
                        else:
                            st.session_state["transaction_csv_upload_id"] = upload_id + 1
                            st.session_state["selected_month"] = max(tx.month_key for tx in transactions)
                            st.session_state["csv_import_count"] = len(transactions)
                            st.rerun()

    if imported := st.session_state.pop("csv_import_count", None):
        st.success(f"Đã nhập thành công {imported} giao dịch.")

    tc_left, tc_right = st.columns([0.85, 1.65], gap="large")

    with tc_left:
        st.html('<div class="glass-panel"><div style="font-size:17px; font-weight:800;">➕ Ghi khoản Thu / Chi mới</div><div style="font-size:12.5px; color:var(--text-muted);">Dữ liệu được kiểm tra hợp lệ và lưu thẳng vào SQLite</div></div>')
        tx_type_in = st.radio("Loại giao dịch:", ["Chi tiêu", "Thu nhập"], horizontal=True, key="tx_type")
        cat_dict = backend.get_categories(tx_type_in)

        if st.session_state.pop("reset_transaction_form", False):
            for key in ("tx_amount", "tx_date", "tx_note", "tx_category"):
                st.session_state.pop(key, None)
        with st.form("emerald_tx_form"):
            st.markdown("**Số tiền (đ)**")
            tx_amount = st.number_input(
                "Số tiền (đ)",
                min_value=0,
                max_value=500_000_000,
                value=50_000,
                step=5_000,
                key="tx_amount",
                label_visibility="collapsed"
            )
            tx_date = st.date_input("Ngày chi / thu:", value=date.today(), key="tx_date")
            tx_cat = st.selectbox(
                "Danh mục:",
                options=list(cat_dict.keys()),
                key="tx_category",
                format_func=lambda c: f"{cat_dict[c]['icon']} {c}"
            )
            tx_note = st.text_input("Ghi chú:", placeholder="VD: Ăn trưa, Xe buýt, Tiền phòng...", key="tx_note")

            submit_tx = st.form_submit_button("Nhập khoản giao dịch", use_container_width=True, type="primary")
            if submit_tx:
                ok, msg = backend.add_daily_transaction(
                    date_str=tx_date.strftime("%Y-%m-%d"),
                    tx_type=tx_type_in,
                    category=tx_cat,
                    amount=float(tx_amount),
                    note=tx_note
                )
                if ok:
                    st.session_state["selected_month"] = tx_date.isoformat()[:7]
                    st.session_state["reset_transaction_form"] = True
                    st.session_state["saved_transaction_notice"] = msg
                    st.rerun()
                else:
                    st.error(f"⚠️ {msg}")
        if saved_notice := st.session_state.pop("saved_transaction_notice", None):
            st.success(f"✅ {saved_notice}")

    with tc_right:
        f1, f2, f3, f4 = st.columns([1, 1, 1.4, 1], vertical_alignment="bottom")
        with f1:
            f_type = st.selectbox("Lọc loại:", ["Tất cả", "Chi tiêu", "Thu nhập"])
        with f2:
            cat_opts = ["Tất cả"] + sorted(df_month["category"].unique().tolist()) if not df_month.empty else ["Tất cả"]
            f_cat = st.selectbox("Lọc danh mục:", cat_opts)
        with f3:
            f_kw = st.text_input("Tìm ghi chú:", placeholder="VD: cơm, xăng, trọ...", key="ledger_search")

        df_show = df_month.copy()
        if f_type != "Tất cả":
            df_show = df_show[df_show["tx_type"] == f_type]
        if f_cat != "Tất cả":
            df_show = df_show[df_show["category"] == f_cat]
        if f_kw.strip():
            df_show = df_show[df_show["note"].str.contains(f_kw.strip(), case=False, na=False, regex=False)]

        with f4:
            if not df_show.empty:
                df_export = df_show.sort_values(by=["date", "id"], ascending=[True, True]).reset_index(drop=True)
                df_export.insert(0, "STT", range(1, len(df_export) + 1))
                df_export["Ngày giao dịch"] = pd.to_datetime(df_export["date"]).dt.strftime("%d/%m/%Y")
                df_export["Số tiền (VNĐ)"] = df_export["amount"].astype(int)
                df_csv = df_export[["STT", "id", "Ngày giao dịch", "tx_type", "category", "Số tiền (VNĐ)", "note"]].rename(
                    columns={"id": "Mã GD", "tx_type": "Loại giao dịch", "category": "Danh mục", "note": "Ghi chú chi tiết"}
                )
                exp_thu = int(df_show[df_show["tx_type"] == "Thu nhập"]["amount"].sum())
                exp_chi = int(df_show[df_show["tx_type"] == "Chi tiêu"]["amount"].sum())
                summary_rows = pd.DataFrame([
                    {"STT": "", "Mã GD": "", "Ngày giao dịch": "", "Loại giao dịch": "TỔNG THU", "Danh mục": "", "Số tiền (VNĐ)": exp_thu, "Ghi chú chi tiết": "Tổng cộng thu nhập"},
                    {"STT": "", "Mã GD": "", "Ngày giao dịch": "", "Loại giao dịch": "TỔNG CHI", "Danh mục": "", "Số tiền (VNĐ)": exp_chi, "Ghi chú chi tiết": "Tổng cộng chi tiêu"},
                    {"STT": "", "Mã GD": "", "Ngày giao dịch": "", "Loại giao dịch": "CHÊNH LỆCH", "Danh mục": "", "Số tiền (VNĐ)": exp_thu - exp_chi, "Ghi chú chi tiết": "Tổng Thu - Tổng Chi"},
                ])
                csv_bytes = pd.concat([df_csv, summary_rows], ignore_index=True).to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 Xuất CSV", data=csv_bytes, file_name=f"UTH_chi_tieu_{selected_month}.csv", mime="text/csv", use_container_width=True)


        if not df_show.empty:
            df_disp = df_show.copy()
            df_disp["Ngày"] = pd.to_datetime(df_disp["date"]).dt.strftime("%d/%m/%Y")
            df_disp["Loại"] = df_disp["tx_type"].map({"Chi tiêu": "🔴 Chi tiêu", "Thu nhập": "🟢 Thu nhập"})
            df_disp["Số tiền"] = df_disp["amount"].apply(format_vnd)
            st.dataframe(
                df_disp[["id", "Ngày", "Loại", "category", "Số tiền", "note"]],
                use_container_width=True,
                hide_index=True,
                height=420,
                column_config={
                    "id": st.column_config.NumberColumn("Mã", width="small"),
                    "Ngày": st.column_config.TextColumn("Ngày", width="small"),
                    "Loại": st.column_config.TextColumn("Loại", width="small"),
                    "category": st.column_config.TextColumn("Danh mục", width="medium"),
                    "Số tiền": st.column_config.TextColumn("Số tiền", width="small"),
                    "note": st.column_config.TextColumn("Ghi chú chi tiết", width="large"),
                }
            )
            with st.expander("🗑️ Xóa giao dịch nhập nhầm hoặc khôi phục dữ liệu mẫu"):
                dc1, dc2, dc3 = st.columns([2.2, 1, 1.2])
                with dc1:
                    tx_map = {row["id"]: f"#{row['id']} | {row['date']} | {row['category']} | {format_vnd(row['amount'])}" for _, row in df_show.iterrows()}
                    del_id = st.selectbox("Chọn giao dịch:", list(tx_map.keys()), format_func=lambda x: tx_map[x], label_visibility="collapsed")
                with dc2:
                    if st.button("Xóa dòng", use_container_width=True):
                        if backend.remove_transaction(int(del_id)):
                            st.toast(f"Đã xóa #{del_id}", icon="🗑️")
                            st.rerun()
                with dc3:
                    if st.button("🔄 Dữ liệu mẫu", use_container_width=True):
                        backend.reset_demo_data()
                        st.toast("Đã nạp lại dữ liệu mẫu!", icon="💚")
                        st.rerun()
        else:
            st.info("Chưa có giao dịch nào phù hợp với bộ lọc.")


# =============================================================================
# TRANG 4: CẢNH BÁO & THIẾT LẬP NGÂN SÁCH + GIẢ LẬP
# =============================================================================
elif st.session_state.nav_page == "Cảnh báo & Ngân sách":
    b1, b2 = st.columns([1.15, 1], gap="large")
    with b1:
        st.markdown("#### 🚨 Trạng thái cảnh báo ngân sách")
        for a in alerts:
            if a["level"] == "danger":
                st.error(f"🚨 **{a['scope']}**: {a['message']}")
            elif a["level"] == "warning":
                st.warning(f"⚠️ **{a['scope']}**: {a['message']}")
            else:
                st.success(f"✅ **{a['scope']}**: {a['message']}")

        spent_by_cat = dashboard_data["spent_by_cat"]
        cmp_rows = []
        for cat in EXPENSE_CATEGORIES:
            cmp_rows.append({"Danh mục": cat, "Loại": "1. Thực chi", "Số tiền": spent_by_cat.get(cat, 0.0)})
            cmp_rows.append({"Danh mục": cat, "Loại": "2. Định mức", "Số tiền": budget_cfg.category_limits.get(cat, 0.0)})
        cmp_chart = (
            alt.Chart(pd.DataFrame(cmp_rows))
            .mark_bar(cornerRadiusEnd=5)
            .encode(
                y=alt.Y("Danh mục:N", title=None, sort="-x"),
                x=alt.X("Số tiền:Q", title="Số tiền (VNĐ)"),
                yOffset="Loại:N",
                color=alt.Color("Loại:N", scale=alt.Scale(domain=["1. Thực chi", "2. Định mức"], range=["#EF4444", "#10B981"])),
                tooltip=[alt.Tooltip("Danh mục:N"), alt.Tooltip("Loại:N"), alt.Tooltip("Số tiền:Q", format=",.0f")]
            )
            .properties(height=320, title="Đối chiếu Thực chi vs Định mức")
        )
        st.altair_chart(cmp_chart, use_container_width=True)

    with b2:
        st.markdown(f"#### ⚙️ Điều chỉnh định mức ({selected_month})")
        with st.form(f"emerald_budget_form_{selected_month}"):
            new_tot = st.number_input("Tổng ngân sách tháng (VNĐ):", min_value=500_000, max_value=100_000_000, value=int(budget_cfg.total_budget), step=100_000, key=f"budget_total_{selected_month}")
            new_lims = {}
            for cat, meta in EXPENSE_CATEGORIES.items():
                new_lims[cat] = float(
                    st.number_input(
                        f"{meta['icon']} {cat}:",
                        min_value=0,
                        max_value=50_000_000,
                        value=int(budget_cfg.category_limits.get(cat, 300_000)),
                        step=50_000,
                        key=f"em_lim_{selected_month}_{cat}"
                    )
                )
            if st.form_submit_button("💾 Lưu cấu hình ngân sách", type="primary", use_container_width=True):
                backend.update_budget(selected_month, float(new_tot), new_lims)
                st.toast("Đã lưu định mức mới!", icon="💚")
                st.rerun()
