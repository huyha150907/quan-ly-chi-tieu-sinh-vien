# -*- coding: utf-8 -*-
"""
Module app.py (Giao diện UniSpend 3D — Thiết kế chuẩn theo mẫu Canva)
-------------------------------------------------------------------------
Tái hiện trung thực phong cách thiết kế của file Canva "UniSpend 3D":
- Nền Gradient xanh băng - tím nhạt dịu mắt (#F4F7FF -> #E9EFFF).
- Thanh điều hướng (Top Navbar) bo tròn nổi màu trắng với gạch chân tím (#6328E8).
- Màn hình 1 (Tổng quan): Thẻ Số dư hiện tại, Tổng thu, Tổng chi, hộp Cảnh báo
  vượt ngân sách màu vàng pastel, Ví 3D tím-hồng nổi bật bên phải, cùng thống kê
  chi tiết Tiền ăn • Tiền trọ • Đi lại.
- Màn hình 2 (Thu chi): Bố cục 2 cột chuẩn Canva (trái: nhập khoản thu/chi hằng ngày;
  phải: bảng lịch sử giao dịch + lọc + xuất CSV + xóa dòng).
- Màn hình 3 (Biểu đồ & Ngân sách): Biểu đồ chi tiêu theo tháng & cài đặt định mức.
- Màn hình 4 (Việc cần làm): Danh sách nhắc việc tài chính sinh viên tương tác.
- Liên kết trực tiếp với `backend.py` (ExpenseBackend) bên trong IDE.
"""

import base64
import os
from csv import Error as CsvError
from datetime import date
from html import escape
from pathlib import Path
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
    initial_sidebar_state="collapsed",
)


def format_vnd(amount: float) -> str:
    """Định dạng số tiền chuẩn VNĐ (VD: 1.250.000 đ)."""
    return f"{amount:,.0f} đ".replace(",", ".")


# =============================================================================
# 2. CSS CHUẨN MẪU CANVA UNISPEND 3D & HIỆU ỨNG TƯƠNG TÁC
# =============================================================================
def inject_canva_unispend_styles():
    st.html("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        :root {
            --navy: #0B1938;
            --purple: #6328E8;
            --purple-soft: #EDE9FE;
            --purple-glow: rgba(99, 40, 232, 0.22);
            --pink: #EC4899;
            --warn-bg: #FEF3C7;
            --warn-text: #D97706;
            --danger-bg: #FEE2E2;
            --danger-text: #DC2626;
            --safe-bg: #DCFCE7;
            --safe-text: #16A34A;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--navy);
        }

        /* Nền xanh băng - tím nhạt dịu mắt giống hệt Canva */
        .stApp {
            background:
                radial-gradient(circle at 85% 20%, rgba(167, 139, 250, 0.22) 0%, transparent 45%),
                radial-gradient(circle at 15% 85%, rgba(191, 219, 254, 0.35) 0%, transparent 50%),
                linear-gradient(135deg, #F5F8FF 0%, #EDF2FF 55%, #E8EEFF 100%);
        }

        .block-container {
            padding-top: 1.1rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 1240px !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
            height: 1rem !important;
        }

        /* Ẩn dòng chữ 'Press Enter to submit form / apply' mặc định của Streamlit */
        [data-testid="InputInstructions"] {
            display: none !important;
        }

        /* ================= ANIMATIONS 3D ================= */
        @keyframes walletFloat3D {
            0%, 100% { transform: translateY(0px) rotateY(-4deg) rotateX(2deg); }
            50% { transform: translateY(-10px) rotateY(4deg) rotateX(-2deg); }
        }
        @keyframes cardSlideIn {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ================= TOP NAVBAR (UNISPEND 3D) ================= */
        .canva-navbar {
            background: #FFFFFF;
            border-radius: 18px;
            padding: 12px 28px;
            box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.08);
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 18px;
            border: 1px solid rgba(226, 232, 240, 0.7);
        }
        .brand-logo {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 22px;
            font-weight: 800;
            color: #0B1938;
            letter-spacing: -0.02em;
        }
        .brand-3d {
            background: linear-gradient(135deg, #6328E8 0%, #EC4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 900;
            font-size: 23px;
            text-shadow: 2px 2px 0px rgba(99, 40, 232, 0.15);
        }

        /* Tùy biến Tabs của Streamlit thành thanh menu ngang chuẩn Canva */
        .stTabs [data-baseweb="tab-list"] {
            background: #FFFFFF;
            padding: 6px 18px;
            border-radius: 16px;
            box-shadow: 0 6px 20px -8px rgba(15, 23, 42, 0.07);
            gap: 24px;
            border: 1px solid rgba(226, 232, 240, 0.8);
            margin-bottom: 18px;
        }
        .stTabs [data-baseweb="tab"] {
            font-family: 'Inter', sans-serif !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #475569 !important;
            padding: 10px 6px !important;
            border-bottom: 2px solid transparent !important;
        }
        .stTabs [aria-selected="true"] {
            color: #0B1938 !important;
            border-bottom: 2.5px solid #6328E8 !important;
            background: transparent !important;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #6328E8 !important;
        }

        /* ================= TYPOGRAPHY & CARDS CHUẨN CANVA ================= */
        .page-title-navy {
            font-size: 46px;
            font-weight: 800;
            color: #0B1938;
            letter-spacing: -0.03em;
            line-height: 1.1;
            margin: 6px 0 4px 0;
        }
        .page-subtitle {
            font-size: 15px;
            color: #475569;
            font-weight: 500;
            margin-bottom: 20px;
        }

        .canva-card {
            background: #FFFFFF;
            border-radius: 22px;
            padding: 24px 28px;
            box-shadow: 0 18px 40px -15px rgba(99, 102, 241, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.9);
            transition: transform 0.22s ease, box-shadow 0.22s ease;
            animation: cardSlideIn 0.45s ease-out;
        }
        .canva-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 24px 48px -15px rgba(99, 40, 232, 0.20);
        }

        .card-mini-label {
            font-size: 14px;
            font-weight: 600;
            color: #334155;
            margin-bottom: 4px;
        }
        .big-purple-num {
            font-size: 40px;
            font-weight: 800;
            color: #6328E8;
            letter-spacing: -0.03em;
            line-height: 1.15;
        }
        .mid-purple-num {
            font-size: 24px;
            font-weight: 800;
            color: #6328E8;
            letter-spacing: -0.02em;
        }
        .divider-soft {
            height: 1px;
            background: #E2E8F0;
            margin: 18px 0;
        }

        /* Hộp cảnh báo vàng pastel giống Page 1 Canva */
        .budget-banner-box {
            border-radius: 16px;
            padding: 16px 20px;
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            align-items: center;
            gap: 16px;
            margin-top: 18px;
        }
        .banner-warn {
            background: #FEF3C7;
            color: #D97706;
        }
        .banner-danger {
            background: #FEE2E2;
            color: #DC2626;
        }
        .banner-safe {
            background: #DCFCE7;
            color: #16A34A;
        }

        /* ================= VÍ 3D TÍM-HỒNG (MINH HỌA PAGE 1 CANVA) ================= */
        .wallet-3d-stage {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 12px 0;
            perspective: 1000px;
        }
        .wallet-3d-svg-wrap {
            animation: walletFloat3D 5s ease-in-out infinite;
            filter: drop-shadow(0 24px 32px rgba(99, 40, 232, 0.24));
            transition: transform 0.3s ease;
            cursor: pointer;
        }
        .wallet-3d-svg-wrap:hover {
            transform: scale(1.05) rotateY(8deg);
        }
        .pedestal-3d {
            width: 310px;
            height: 54px;
            background: linear-gradient(180deg, #E0E7FF 0%, #C7D2FE 100%);
            border-radius: 50%;
            margin-top: -26px;
            box-shadow: 0 20px 35px rgba(99, 102, 241, 0.22), inset 0 4px 10px rgba(255,255,255,0.8);
            z-index: 0;
        }

        /* ================= 3 THẺ TIỀN ĂN, TIỀN TRỌ, ĐI LẠI ================= */
        .cat-3d-card {
            background: #FFFFFF;
            border-radius: 20px;
            padding: 20px 22px;
            box-shadow: 0 12px 30px -12px rgba(15, 23, 42, 0.10);
            border: 1px solid #EEF2FF;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .cat-3d-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 38px -12px rgba(99, 40, 232, 0.18);
        }
        .progress-bg {
            width: 100%;
            height: 9px;
            background: #EDE9FE;
            border-radius: 999px;
            overflow: hidden;
            margin: 10px 0 8px 0;
        }
        .progress-bar {
            height: 100%;
            border-radius: 999px;
            transition: width 0.5s ease;
        }

        /* ================= NÚT TÍM CANVA ================= */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #6328E8 0%, #7C3AED 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 10px 22px !important;
            font-weight: 700 !important;
            box-shadow: 0 10px 22px -6px rgba(99, 40, 232, 0.45) !important;
            transition: all 0.2s ease !important;
        }
        div.stButton > button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 14px 28px -6px rgba(99, 40, 232, 0.55) !important;
        }

        /* ================= VIỆC CẦN LÀM (PAGE 4 CANVA) ================= */
        .todo-item-row {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 14px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
        }
        .prio-pill {
            padding: 5px 14px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 700;
            background: #EDE9FE;
            color: #5B21B6;
        }
    </style>
    """)

    # JS tạo hiệu ứng nghiêng 3D nhẹ khi di chuột lên các thẻ .canva-card và .cat-3d-card
    components.html("""
    <script>
    (function() {
        const doc = window.parent.document;
        function bindTilt() {
            const cards = doc.querySelectorAll('.canva-card, .cat-3d-card');
            cards.forEach(card => {
                if (card.dataset.tilt3d === "1") return;
                card.dataset.tilt3d = "1";
                card.addEventListener('mousemove', (e) => {
                    const r = card.getBoundingClientRect();
                    const rx = (((e.clientY - r.top) - r.height / 2) / (r.height / 2)) * -4;
                    const ry = (((e.clientX - r.left) - r.width / 2) / (r.width / 2)) * 4;
                    card.style.transform = `perspective(900px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) translateY(-4px)`;
                });
                card.addEventListener('mouseleave', () => {
                    card.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) translateY(0px)';
                });
            });
        }
        bindTilt();
        setInterval(bindTilt, 800);
    })();
    </script>
    """, height=0, width=0)


# =============================================================================
# 3. KẾT NỐI BACKEND (backend.py)
# =============================================================================
@st.cache_resource
def get_backend(path: str) -> ExpenseBackend:
    return ExpenseBackend(path)


backend = get_backend(str(database_path()))
inject_canva_unispend_styles()
st.html(Path(__file__).with_name("transaction_layout.css"))

available_months = backend.get_available_months()
saved_month = st.session_state.pop("report_month_after_save", None)
if saved_month in available_months:
    st.session_state["report_month"] = saved_month
elif st.session_state.get("report_month") not in available_months:
    st.session_state["report_month"] = available_months[0]

# Khởi tạo danh sách Việc cần làm sinh viên (giống Page 4 Canva)
if "student_todos" not in st.session_state:
    st.session_state.student_todos = [
        {"title": "Nộp bài xác suất", "due": "20/11", "prio": "Cao", "done": False},
        {"title": "Đóng tiền trọ tháng này", "due": "25/11", "prio": "Vừa", "done": False},
        {"title": "Mua giáo trình Python", "due": "15/11", "prio": "Thấp", "done": True},
    ]


# =============================================================================
# 4. THANH HEADER NỔI UNISPEND 3D & BỘ CHỌN THÁNG
# =============================================================================
h_col1, h_col2 = st.columns([3.5, 1])
with h_col1:
    st.html("""
    <div class="unispend-brand">
        <span class="unispend-brand-mark" aria-hidden="true">U</span>
        <div>
            <div class="unispend-brand-name">UniSpend <span>UTH</span></div>
            <div class="unispend-brand-caption">Sổ thu chi sinh viên</div>
        </div>
    </div>
    """)
with h_col2:
    selected_month = st.selectbox(
        "Tháng báo cáo",
        options=available_months,
        key="report_month",
    )

y_str, m_str = selected_month.split("-")

# Lấy toàn bộ dữ liệu tháng từ Backend
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


# =============================================================================
# 5. THANH ĐIỀU HƯỚNG 4 MÀN HÌNH CHUẨN CANVA
# =============================================================================
tab_tong_quan, tab_thu_chi, tab_bieu_do, tab_viec_can_lam = st.tabs([
    "Tổng quan",
    "Thu chi",
    "Biểu đồ & Ngân sách",
    "Việc cần làm"
])


# =============================================================================
# MÀN HÌNH 1: TỔNG QUAN (GIỐNG PAGE 1 CANVA + THỐNG KÊ ĂN/TRỌ/ĐI LẠI)
# =============================================================================
with tab_tong_quan:
    left_hero, right_hero = st.columns([1.05, 1.15], gap="large")

    with left_hero:
        if budget_used_pct > 100:
            banner_cls = "banner-danger"
            banner_msg = f"Báo động vượt ngân sách!<br>Đã vượt {format_vnd(abs(budget_remaining))}"
        elif budget_used_pct >= 80:
            banner_cls = "banner-warn"
            banner_msg = "Cảnh báo<br>sắp vượt ngân sách"
        else:
            banner_cls = "banner-safe"
            banner_msg = f"An toàn chi tiêu<br>Còn {format_vnd(budget_remaining)}"

        st.html(f"""
        <div class="page-title-navy">Tổng quan</div>
        <div class="page-subtitle">Tháng {m_str}/{y_str}</div>

        <div class="canva-card">
            <div class="card-mini-label">Số dư hiện tại</div>
            <div class="big-purple-num">{format_vnd(balance)}</div>

            <div class="divider-soft"></div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                <div style="border-right:1px solid #E2E8F0; padding-right:12px;">
                    <div class="card-mini-label">Tổng thu</div>
                    <div class="mid-purple-num">{format_vnd(total_income)}</div>
                </div>
                <div style="padding-left:4px;">
                    <div class="card-mini-label">Tổng chi</div>
                    <div class="mid-purple-num">{format_vnd(total_expense)}</div>
                </div>
            </div>

            <div class="budget-banner-box {banner_cls}">
                <div style="border-right:1px solid rgba(0,0,0,0.08); padding-right:12px;">
                    <div style="font-size:13px; font-weight:600; color:#1E293B; margin-bottom:2px;">Ngân sách đã dùng</div>
                    <div style="font-size:32px; font-weight:800; line-height:1.1;">{budget_used_pct:.0f}%</div>
                </div>
                <div style="font-size:16px; font-weight:700; line-height:1.35;">
                    {banner_msg}
                </div>
            </div>
        </div>
        """)

    with right_hero:
        # Hiển thị ảnh minh họa Ví & Chi tiêu sinh viên bên phải
        wallet_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "wallet_3d.jpg")
        if os.path.exists(wallet_img_path):
            with open(wallet_img_path, "rb") as img_f:
                img_b64 = base64.b64encode(img_f.read()).decode("utf-8")
            st.html(f"""
            <div style="display:flex; justify-content:center; align-items:center; padding-top: 24px;">
                <img src="data:image/jpeg;base64,{img_b64}"
                     alt="Minh họa chi tiêu sinh viên UTH"
                     style="width:100%; max-width:440px; border-radius:28px; box-shadow: 0 24px 50px -12px rgba(99, 40, 232, 0.25); animation: walletFloat3D 5s ease-in-out infinite;" />
            </div>
            """)

    # Phần thống kê 3 khoản thiết yếu Tiền ăn, Tiền trọ, Đi lại ngay bên dưới
    st.html('<div style="font-size:20px; font-weight:800; color:#0B1938; margin:14px 0 10px 0;">Thống kê Tiền ăn • Tiền trọ • Đi lại</div>')
    e_cols = st.columns(3, gap="medium")
    for idx, item in enumerate(essential_stats):
        pct_bar = min(item["percent"], 100.0)
        if item["status"] == "danger":
            bar_col = "#EF4444"
            badge_bg, badge_txt = "#FEE2E2", "#DC2626"
        elif item["status"] == "warning":
            bar_col = "#F59E0B"
            badge_bg, badge_txt = "#FEF3C7", "#D97706"
        else:
            bar_col = "#6328E8"
            badge_bg, badge_txt = "#EDE9FE", "#5B21B6"

        with e_cols[idx]:
            st.html(f"""
            <div class="cat-3d-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:16px; font-weight:700; color:#0B1938;">{item['icon']} {item['category']}</span>
                    <span style="font-size:12px; font-weight:700; padding:4px 10px; border-radius:99px; background:{badge_bg}; color:{badge_txt};">
                        {item['percent']:.1f}%
                    </span>
                </div>
                <div style="font-size:24px; font-weight:800; color:#6328E8;">{format_vnd(item['spent'])}</div>
                <div style="font-size:12.5px; color:#64748B; margin-top:2px;">
                    Định mức: <strong>{format_vnd(item['limit'])}</strong> • Chiếm {item['share_of_total']:.1f}%
                </div>
                <div class="progress-bg">
                    <div class="progress-bar" style="width:{pct_bar:.1f}%; background:{bar_col};"></div>
                </div>
                <div style="font-size:12.5px; font-weight:600; color:#334155;">{item['note_text']}</div>
            </div>
            """)


# =============================================================================
# MÀN HÌNH 2: THU CHI (BỐ CỤC 2 CỘT CHUẨN PAGE 2 CANVA)
# =============================================================================
with tab_thu_chi:
    st.html(f"""
    <div class="transaction-header">
        <div>
            <h2>Thu chi</h2>
            <p>Tháng {m_str}/{y_str} · {len(df_month)} giao dịch</p>
        </div>
        <div class="transaction-header-balance">
            <span>Số dư trong tháng</span>
            <strong>{format_vnd(balance)}</strong>
        </div>
    </div>
    """)

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
                            st.session_state["report_month_after_save"] = max(tx.month_key for tx in transactions)
                            st.session_state["csv_import_count"] = len(transactions)
                            st.rerun()

    if imported := st.session_state.pop("csv_import_count", None):
        st.success(f"Đã nhập thành công {imported} giao dịch.")

    tc_left, tc_right = st.columns([1, 2], gap="large")
    with tc_left:
        st.subheader("Thêm giao dịch")
        tx_type_in = st.radio("Loại giao dịch:", ["Chi tiêu", "Thu nhập"], horizontal=True)
        cat_dict = backend.get_categories(tx_type_in)

        if st.session_state.pop("reset_transaction_form", False):
            for key in ("tx_amount", "tx_date", "tx_note", "tx_category"):
                st.session_state.pop(key, None)
        with st.form("canva_tx_form"):
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
            st.markdown("**Thông tin khoản chi / thu**")
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
                    st.session_state["report_month_after_save"] = tx_date.isoformat()[:7]
                    st.session_state["reset_transaction_form"] = True
                    st.session_state["saved_transaction_notice"] = msg
                    st.rerun()
                else:
                    st.error(f"⚠️ {msg}")
        if saved_notice := st.session_state.pop("saved_transaction_notice", None):
            st.success(f"✅ {saved_notice}")

    with tc_right:
        st.subheader("Sổ giao dịch")

        f1, f2, f3 = st.columns([1, 1, 1.4])
        with f1:
            f_type = st.selectbox("Lọc loại:", ["Tất cả", "Chi tiêu", "Thu nhập"])
        with f2:
            cat_opts = ["Tất cả"] + sorted(df_month["category"].unique().tolist()) if not df_month.empty else ["Tất cả"]
            f_cat = st.selectbox("Lọc danh mục:", cat_opts)
        with f3:
            f_kw = st.text_input("Tìm ghi chú:", placeholder="VD: cơm, xăng, tiền trọ...", key="ledger_search")
        with st.container():
            df_show = df_month.copy()
            if f_type != "Tất cả":
                df_show = df_show[df_show["tx_type"] == f_type]
            if f_cat != "Tất cả":
                df_show = df_show[df_show["category"] == f_cat]
            if f_kw.strip():
                df_show = df_show[df_show["note"].str.contains(f_kw.strip(), case=False, na=False, regex=False)]

            if not df_show.empty:
                df_export = df_show.sort_values(by=["date", "id"], ascending=[True, True]).reset_index(drop=True)
                df_export.insert(0, "STT", range(1, len(df_export) + 1))
                df_export["Ngày giao dịch"] = pd.to_datetime(df_export["date"]).dt.strftime("%d/%m/%Y")
                df_export["Số tiền (VNĐ)"] = df_export["amount"].astype(int)
                df_csv = df_export[["STT", "id", "Ngày giao dịch", "tx_type", "category", "Số tiền (VNĐ)", "note"]].rename(
                    columns={
                        "id": "Mã GD",
                        "tx_type": "Loại giao dịch",
                        "category": "Danh mục",
                        "note": "Ghi chú chi tiết",
                    }
                )
                exp_thu = int(df_show[df_show["tx_type"] == "Thu nhập"]["amount"].sum())
                exp_chi = int(df_show[df_show["tx_type"] == "Chi tiêu"]["amount"].sum())
                summary_rows = pd.DataFrame([
                    {"STT": "", "Mã GD": "", "Ngày giao dịch": "", "Loại giao dịch": "TỔNG THU", "Danh mục": "", "Số tiền (VNĐ)": exp_thu, "Ghi chú chi tiết": f"Tổng cộng thu nhập ({len(df_show[df_show['tx_type']=='Thu nhập'])} khoản)"},
                    {"STT": "", "Mã GD": "", "Ngày giao dịch": "", "Loại giao dịch": "TỔNG CHI", "Danh mục": "", "Số tiền (VNĐ)": exp_chi, "Ghi chú chi tiết": f"Tổng cộng chi tiêu ({len(df_show[df_show['tx_type']=='Chi tiêu'])} khoản)"},
                    {"STT": "", "Mã GD": "", "Ngày giao dịch": "", "Loại giao dịch": "CHÊNH LỆCH", "Danh mục": "", "Số tiền (VNĐ)": exp_thu - exp_chi, "Ghi chú chi tiết": "Tổng Thu - Tổng Chi"},
                ])
                df_csv_full = pd.concat([df_csv, summary_rows], ignore_index=True)
                csv_bytes = df_csv_full.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📥 Xuất CSV",
                    data=csv_bytes,
                    file_name=f"UTH_chi_tieu_{selected_month}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        if not df_show.empty:
            sum_thu = float(df_show[df_show["tx_type"] == "Thu nhập"]["amount"].sum())
            sum_chi = float(df_show[df_show["tx_type"] == "Chi tiêu"]["amount"].sum())
            sum_diff = sum_thu - sum_chi
            st.html(f"""
            <div class="transaction-totals">
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:14px; padding:10px 14px;">
                    <div style="font-size:11px; color:#64748B; font-weight:600;">Số dòng hiển thị</div>
                    <div style="font-size:17px; font-weight:800; color:#0B1938;">{len(df_show)} khoản</div>
                </div>
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:14px; padding:10px 14px;">
                    <div style="font-size:11px; color:#15803D; font-weight:600;">Tổng Thu (lọc)</div>
                    <div style="font-size:17px; font-weight:800; color:#16A34A;">{format_vnd(sum_thu)}</div>
                </div>
                <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:14px; padding:10px 14px;">
                    <div style="font-size:11px; color:#B91C1C; font-weight:600;">Tổng Chi (lọc)</div>
                    <div style="font-size:17px; font-weight:800; color:#DC2626;">{format_vnd(sum_chi)}</div>
                </div>
                <div style="background:#EDE9FE; border:1px solid #DDD6FE; border-radius:14px; padding:10px 14px;">
                    <div style="font-size:11px; color:#5B21B6; font-weight:600;">Chênh lệch</div>
                    <div style="font-size:17px; font-weight:800; color:#6328E8;">{format_vnd(sum_diff)}</div>
                </div>
            </div>
            """)

            df_display = df_show.copy()
            df_display["Ngày"] = pd.to_datetime(df_display["date"]).dt.strftime("%d/%m/%Y")
            df_display["Loại"] = df_display["tx_type"].map({"Chi tiêu": "🔴 Chi tiêu", "Thu nhập": "🟢 Thu nhập"})
            df_display["Số tiền"] = df_display["amount"].apply(format_vnd)

            st.dataframe(
                df_display[["id", "Ngày", "Loại", "category", "Số tiền", "note"]],
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
            with st.expander("🗑️ Xóa giao dịch nhập nhầm hoặc nạp lại dữ liệu mẫu"):
                d_c1, d_c2, d_c3 = st.columns([2.2, 1, 1.2])
                with d_c1:
                    tx_map = {
                        row["id"]: f"#{row['id']} | {row['date']} | {row['category']} | {format_vnd(row['amount'])}"
                        for _, row in df_show.iterrows()
                    }
                    del_id = st.selectbox("Chọn giao dịch:", list(tx_map.keys()), format_func=lambda x: tx_map[x], label_visibility="collapsed")
                with d_c2:
                    if st.button("Xóa dòng", use_container_width=True):
                        if backend.remove_transaction(int(del_id)):
                            st.toast(f"Đã xóa #{del_id}", icon="🗑️")
                            st.rerun()
                with d_c3:
                    if st.button("🔄 Dữ liệu mẫu", use_container_width=True):
                        backend.reset_demo_data()
                        st.toast("Đã nạp lại dữ liệu mẫu!", icon="💜")
                        st.rerun()
        else:
            st.info("Chưa có giao dịch nào phù hợp với bộ lọc.")


# =============================================================================
# MÀN HÌNH 3: BIỂU ĐỒ CHI TIÊU THEO THÁNG & CÀI ĐẶT NGÂN SÁCH
# =============================================================================
with tab_bieu_do:
    st.html(f'<div class="page-title-navy" style="font-size:34px;">Biểu đồ chi tiêu theo tháng</div><div class="page-subtitle">Phân tích xu hướng thu chi và kiểm soát định mức tháng {m_str}/{y_str}</div>')

    df_monthly_io = charts_data["monthly_io"]
    df_monthly_cat = charts_data["monthly_cat"]
    df_core3 = charts_data["core3_trend"]
    df_pie = charts_data["pie_month"]

    c_top1, c_top2 = st.columns(2, gap="medium")
    with c_top1:
        if not df_monthly_io.empty:
            bar_io = (
                alt.Chart(df_monthly_io)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=26)
                .encode(
                    x=alt.X("month:N", title="Tháng", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("amount:Q", title="Số tiền (VNĐ)"),
                    xOffset="tx_type:N",
                    color=alt.Color("tx_type:N", title="Loại", scale=alt.Scale(domain=["Thu nhập", "Chi tiêu"], range=["#6328E8", "#EC4899"])),
                    tooltip=[alt.Tooltip("month:N"), alt.Tooltip("tx_type:N"), alt.Tooltip("amount:Q", format=",.0f")]
                )
                .properties(height=300, title="So sánh Thu nhập và Chi tiêu theo Tháng")
            )
            st.altair_chart(bar_io, use_container_width=True)

    with c_top2:
        if not df_pie.empty:
            donut = (
                alt.Chart(df_pie)
                .mark_arc(innerRadius=58, outerRadius=108, cornerRadius=6)
                .encode(
                    theta=alt.Theta("amount:Q"),
                    color=alt.Color("category:N", title="Danh mục", scale=alt.Scale(scheme="purples")),
                    tooltip=[alt.Tooltip("category:N"), alt.Tooltip("amount:Q", format=",.0f"), alt.Tooltip("pct:Q", format=".1f")]
                )
                .properties(height=300, title=f"Cơ cấu chi tiêu tháng {selected_month}")
            )
            st.altair_chart(donut, use_container_width=True)

    if not df_core3.empty:
        line_c3 = (
            alt.Chart(df_core3)
            .mark_line(point=alt.OverlayMarkDef(size=90, filled=True), strokeWidth=3, interpolate="monotone")
            .encode(
                x=alt.X("month:N", title="Tháng", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("amount:Q", title="VNĐ"),
                color=alt.Color(
                    "category:N",
                    title="Nhóm trọng tâm",
                    scale=alt.Scale(domain=["Tiền ăn", "Tiền trọ", "Đi lại"], range=["#EC4899", "#6328E8", "#0EA5E9"])
                ),
                tooltip=[alt.Tooltip("month:N"), alt.Tooltip("category:N"), alt.Tooltip("amount:Q", format=",.0f")]
            )
            .properties(height=270, title="Biến động Tiền ăn • Tiền trọ • Đi lại qua các tháng")
        )
        st.altair_chart(line_c3, use_container_width=True)

    st.markdown("---")
    st.markdown(f"#### 📋 Bảng thống kê chi tiết từng danh mục tháng {m_str}/{y_str}")
    if not df_category_summary.empty:
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
        cat_csv = df_category_summary.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Xuất CSV Thống kê theo Danh mục",
            data=cat_csv,
            file_name=f"UTH_thong_ke_danh_muc_{selected_month}.csv",
            mime="text/csv"
        )

    st.markdown("---")
    b_left, b_right = st.columns([1.15, 1], gap="large")
    with b_left:
        st.markdown("#### 🚨 Cảnh báo ngân sách hiện tại")
        for a in alerts:
            if a["level"] == "danger":
                st.error(f"🚨 **{a['scope']}**: {a['message']}")
            elif a["level"] == "warning":
                st.warning(f"⚠️ **{a['scope']}**: {a['message']}")
            else:
                st.success(f"✅ **{a['scope']}**: {a['message']}")
    with b_right:
        st.markdown(f"#### ⚙️ Điều chỉnh định mức ({selected_month})")
        with st.form("canva_budget_form"):
            new_tot = st.number_input("Tổng ngân sách tháng (đ):", min_value=500_000, max_value=100_000_000, value=int(budget_cfg.total_budget), step=100_000, key=f"budget_total_{selected_month}")
            new_lims = {}
            for cat, meta in EXPENSE_CATEGORIES.items():
                new_lims[cat] = float(
                    st.number_input(
                        f"{meta['icon']} {cat}:",
                        min_value=0,
                        max_value=50_000_000,
                        value=int(budget_cfg.category_limits.get(cat, 300_000)),
                        step=50_000,
                        key=f"canva_lim_{selected_month}_{cat}"
                    )
                )
            if st.form_submit_button("Lưu định mức ngân sách", use_container_width=True, type="primary"):
                backend.update_budget(selected_month, float(new_tot), new_lims)
                st.toast("Đã cập nhật ngân sách!", icon="💜")
                st.rerun()


# =============================================================================
# MÀN HÌNH 4: VIỆC CẦN LÀM (GIỐNG PAGE 4 CANVA)
# =============================================================================
with tab_viec_can_lam:
    t_left, t_right = st.columns([0.9, 1.5], gap="large")

    todos = st.session_state.student_todos
    done_cnt = sum(1 for t in todos if t["done"])
    total_cnt = len(todos)
    pct_done = int(done_cnt / total_cnt * 100) if total_cnt > 0 else 0

    with t_left:
        st.html(f"""
        <div class="page-title-navy">Việc cần làm</div>
        <div class="page-subtitle">Theo dõi và hoàn thành các công việc quan trọng đúng hạn</div>
        <div class="canva-card">
            <div class="card-mini-label">Tiến độ hoàn thành</div>
            <div class="big-purple-num">{pct_done}%</div>
            <div style="font-size:14px; color:#64748B; margin-top:6px;">{done_cnt}/{total_cnt} việc đã hoàn thành</div>
        </div>
        """)

        with st.form("add_todo_form", clear_on_submit=True):
            new_t = st.text_input("Thêm việc cần làm mới:", placeholder="VD: Đóng tiền điện tháng 11...")
            t_c1, t_c2 = st.columns(2)
            with t_c1:
                new_due = st.text_input("Hạn chót:", value="30/11")
            with t_c2:
                new_prio = st.selectbox("Mức độ:", ["Cao", "Vừa", "Thấp"])
            if st.form_submit_button("Thêm công việc", use_container_width=True, type="primary"):
                if new_t.strip():
                    st.session_state.student_todos.append({
                        "title": new_t.strip(),
                        "due": new_due.strip(),
                        "prio": new_prio,
                        "done": False
                    })
                    st.rerun()

    with t_right:
        st.html('<div class="canva-card" style="padding:18px 24px;">')
        for idx, todo in enumerate(todos):
            c_chk, c_txt, c_due, c_pri = st.columns([0.4, 3, 0.8, 0.8])
            with c_chk:
                checked = st.checkbox("Hoàn thành", value=todo["done"], key=f"todo_chk_{idx}", label_visibility="collapsed")
                if checked != todo["done"]:
                    st.session_state.student_todos[idx]["done"] = checked
                    st.rerun()
            with c_txt:
                txt_style = "text-decoration: line-through; color: #94A3B8;" if todo["done"] else "color: #0B1938; font-weight: 600;"
                st.html(f'<div style="padding-top:6px; font-size:15px; {txt_style}">{escape(todo["title"])}</div>')
            with c_due:
                st.html(f'<div style="padding-top:6px; font-size:14px; color:#64748B;">{escape(todo["due"])}</div>')
            with c_pri:
                st.html(f'<div style="padding-top:2px;"><span class="prio-pill">{todo["prio"]}</span></div>')
        st.html('</div>')
