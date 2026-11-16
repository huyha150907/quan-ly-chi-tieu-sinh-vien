# -*- coding: utf-8 -*-
"""
Module app.py (Tầng Giao Diện Người Dùng 3D Tương Tác - Frontend UI)
-------------------------------------------------------------------------
File giao diện chính của Ứng dụng Quản lý Chi tiêu Sinh viên (UniSpend).
Phiên bản nâng cấp: Tích hợp Hiệu ứng động 3D (3D Perspective Tilt, 3D Flip Wallet Card,
Floating 3D Orbs, Shimmer Progress Bar, Spotlight Glare & Counter Animation)
và liên kết trực tiếp với `backend.py` (ExpenseBackend) bên trong IDE.
"""

from datetime import date
from pathlib import Path
import pandas as pd
import altair as alt
import streamlit as st
import streamlit.components.v1 as components

# LIÊN KẾT QUA PHẦN BACKEND BÊN IDE
from backend import ExpenseBackend
from models import EXPENSE_CATEGORIES


# =============================================================================
# 1. CẤU HÌNH TRANG STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="UniSpend 3D - Quản Lý Chi Tiêu Sinh Viên",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


def format_vnd(amount: float) -> str:
    """Định dạng số tiền sang chuẩn VNĐ dễ đọc (VD: 1.850.000 đ)."""
    return f"{amount:,.0f} đ".replace(",", ".")


# =============================================================================
# 2. CSS 3D ANIMATIONS, GLASSMORPHISM & JAVASCRIPT 3D INTERACTIVE ENGINE
# =============================================================================
def inject_3d_styles_and_scripts():
    """
    Chèn hệ thống CSS 3D (perspective, preserve-3d, keyframes, glassmorphism,
    shimmer, neon pulse) và kịch bản JS lắng nghe chuyển động chuột để nghiêng
    thẻ 3D (3D Tilt + Glare Spotlight) theo thời gian thực.
    """
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        :root {
            --primary: #4F46E5;
            --primary-glow: rgba(79, 70, 229, 0.45);
            --accent: #06B6D4;
            --danger: #EF4444;
            --warning: #F59E0B;
            --safe: #10B981;
        }

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Nền trang Mesh Gradient nhẹ nhàng tạo chiều sâu không gian 3D */
        .stApp {
            background:
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.09) 0px, transparent 50%),
                radial-gradient(at 98% 10%, rgba(6, 182, 212, 0.09) 0px, transparent 45%),
                radial-gradient(at 50% 100%, rgba(236, 72, 153, 0.06) 0px, transparent 50%),
                #F8FAFC;
        }

        .block-container {
            padding-top: 1.3rem !important;
            padding-bottom: 3rem !important;
            max-width: 1400px;
            perspective: 1400px;
        }

        /* ================= KEYFRAMES ĐỘNG 3D ================= */
        @keyframes float3D {
            0%, 100% { transform: translate3d(0, 0px, 0) rotate(0deg); }
            50% { transform: translate3d(0, -10px, 18px) rotate(3deg); }
        }
        @keyframes orbFloat {
            0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
            50% { transform: translate3d(25px, -18px, 30px) scale(1.12); }
        }
        @keyframes shimmerSweep {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        @keyframes pulseDanger3D {
            0%, 100% {
                box-shadow: 0 8px 24px rgba(239, 68, 68, 0.18), 0 0 0 0 rgba(239, 68, 68, 0.45);
            }
            50% {
                box-shadow: 0 12px 32px rgba(239, 68, 68, 0.32), 0 0 0 8px rgba(239, 68, 68, 0);
            }
        }
        @keyframes slideUp3D {
            from {
                opacity: 0;
                transform: perspective(1000px) translateY(24px) rotateX(-8deg);
            }
            to {
                opacity: 1;
                transform: perspective(1000px) translateY(0) rotateX(0deg);
            }
        }

        /* ================= HERO BANNER 3D + THẺ VÍ SINH VIÊN LẬT 3D ================= */
        .hero-3d-wrapper {
            display: grid;
            grid-template-columns: 1.55fr 1fr;
            gap: 22px;
            margin-bottom: 24px;
            perspective: 1500px;
            animation: slideUp3D 0.65s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @media (max-width: 992px) {
            .hero-3d-wrapper { grid-template-columns: 1fr; }
        }

        .hero-banner-3d {
            background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 48%, #4338CA 100%);
            border-radius: 24px;
            padding: 28px 32px;
            color: #FFFFFF;
            position: relative;
            overflow: hidden;
            box-shadow:
                0 22px 45px -12px rgba(30, 27, 75, 0.45),
                inset 0 1px 1px rgba(255, 255, 255, 0.25);
            transform-style: preserve-3d;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        /* Các khối cầu 3D trôi lơ lửng bên trong Banner */
        .orb-1 {
            position: absolute;
            width: 210px;
            height: 210px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(99,102,241,0.55) 0%, rgba(99,102,241,0) 70%);
            top: -65px;
            right: -35px;
            animation: orbFloat 7s ease-in-out infinite;
            pointer-events: none;
        }
        .orb-2 {
            position: absolute;
            width: 170px;
            height: 170px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(6,182,212,0.45) 0%, rgba(6,182,212,0) 70%);
            bottom: -55px;
            left: 25%;
            animation: orbFloat 9s ease-in-out infinite reverse;
            pointer-events: none;
        }
        .hero-tag {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.22);
            padding: 5px 14px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #A5F3FC;
            width: fit-content;
            margin-bottom: 12px;
            transform: translateZ(30px);
        }
        .hero-title-3d {
            font-size: 1.85rem;
            font-weight: 800;
            margin: 0 0 8px 0;
            letter-spacing: -0.02em;
            line-height: 1.2;
            transform: translateZ(45px);
            text-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
        }
        .hero-desc-3d {
            font-size: 0.94rem;
            color: #E0E7FF;
            margin: 0 0 18px 0;
            max-width: 92%;
            transform: translateZ(25px);
        }
        .hero-pills-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            transform: translateZ(35px);
        }
        .hero-mini-pill {
            background: rgba(15, 23, 42, 0.55);
            border: 1px solid rgba(255, 255, 255, 0.16);
            padding: 7px 14px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            color: #F8FAFC;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: transform 0.2s ease, background 0.2s ease;
        }
        .hero-mini-pill:hover {
            transform: translateY(-3px) scale(1.04);
            background: rgba(79, 70, 229, 0.65);
        }

        /* ================= THẺ VÍ SINH VIÊN LẬT 3D (3D FLIP WALLET CARD) ================= */
        .wallet-scene {
            width: 100%;
            height: 215px;
            perspective: 1200px;
            cursor: pointer;
        }
        .wallet-card-3d {
            width: 100%;
            height: 100%;
            position: relative;
            transition: transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            transform-style: preserve-3d;
        }
        .wallet-scene:hover .wallet-card-3d {
            transform: rotateY(180deg);
        }
        .wallet-face {
            position: absolute;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            -webkit-backface-visibility: hidden;
            border-radius: 24px;
            padding: 22px 26px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow:
                0 20px 40px -15px rgba(15, 23, 42, 0.38),
                inset 0 1px 2px rgba(255, 255, 255, 0.35);
            overflow: hidden;
        }
        .wallet-front {
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #EC4899 100%);
            color: white;
        }
        .wallet-front::after {
            content: "";
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(
                45deg,
                transparent 40%,
                rgba(255, 255, 255, 0.18) 50%,
                transparent 60%
            );
            background-size: 200% 200%;
            animation: shimmerSweep 5s infinite linear;
            pointer-events: none;
        }
        .wallet-back {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 60%, #334155 100%);
            color: #F8FAFC;
            transform: rotateY(180deg);
            border: 1px solid rgba(148, 163, 184, 0.3);
        }
        .chip-3d {
            width: 44px;
            height: 32px;
            border-radius: 8px;
            background: linear-gradient(135deg, #FDE68A 0%, #F59E0B 100%);
            box-shadow: inset 0 1px 2px rgba(255,255,255,0.6), 0 2px 6px rgba(0,0,0,0.25);
            position: relative;
        }
        .flip-hint {
            font-size: 0.73rem;
            background: rgba(255, 255, 255, 0.2);
            padding: 4px 10px;
            border-radius: 99px;
            font-weight: 600;
            backdrop-filter: blur(4px);
        }

        /* ================= THẺ KPI 3D NGHIÊNG THEO CHUỘT (TILT 3D CARDS) ================= */
        .kpi-card-3d {
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(14px);
            border-radius: 22px;
            padding: 22px 24px;
            border: 1px solid rgba(226, 232, 240, 0.95);
            box-shadow:
                0 12px 28px -8px rgba(15, 23, 42, 0.07),
                0 2px 6px -1px rgba(15, 23, 42, 0.04),
                inset 0 1px 0 rgba(255, 255, 255, 1);
            transform-style: preserve-3d;
            transition: transform 0.18s ease-out, box-shadow 0.25s ease, border-color 0.25s ease;
            position: relative;
            overflow: hidden;
            cursor: pointer;
            animation: slideUp3D 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .kpi-card-3d:hover {
            box-shadow:
                0 24px 42px -12px rgba(79, 70, 229, 0.22),
                0 4px 12px rgba(15, 23, 42, 0.06);
            border-color: rgba(99, 102, 241, 0.45);
        }
        .kpi-top-3d {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            transform: translateZ(28px);
        }
        .kpi-label-3d {
            font-size: 0.82rem;
            font-weight: 700;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .kpi-icon-3d {
            width: 46px;
            height: 46px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            box-shadow: 0 8px 16px -4px rgba(0, 0, 0, 0.12);
            animation: float3D 4s ease-in-out infinite;
        }
        .kpi-value-3d {
            font-size: 1.6rem;
            font-weight: 800;
            margin-bottom: 6px;
            letter-spacing: -0.02em;
            transform: translateZ(42px);
        }
        .kpi-sub-3d {
            font-size: 0.82rem;
            font-weight: 600;
            transform: translateZ(20px);
        }

        /* ================= 3 THẺ TIỀN ĂN, TIỀN TRỌ, ĐI LẠI 3D ================= */
        .essential-card-3d {
            background: linear-gradient(165deg, #FFFFFF 0%, #F8FAFC 100%);
            border-radius: 22px;
            padding: 24px;
            border: 1px solid #E2E8F0;
            box-shadow:
                0 14px 30px -10px rgba(15, 23, 42, 0.07),
                inset 0 1px 0 rgba(255, 255, 255, 0.9);
            transform-style: preserve-3d;
            transition: transform 0.2s ease-out, box-shadow 0.25s ease, border-color 0.25s ease;
            position: relative;
            overflow: hidden;
            margin-bottom: 14px;
        }
        .essential-card-3d:hover {
            box-shadow:
                0 26px 48px -12px rgba(15, 23, 42, 0.16),
                0 0 0 1px rgba(99, 102, 241, 0.35);
        }
        .essential-header-3d {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
            transform: translateZ(30px);
        }
        .essential-icon-badge {
            width: 48px;
            height: 48px;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.55rem;
            box-shadow: 0 10px 20px -6px rgba(0, 0, 0, 0.15);
            animation: float3D 4.5s ease-in-out infinite;
        }
        .essential-title-text {
            font-size: 1.18rem;
            font-weight: 800;
            color: #0F172A;
        }
        .essential-pill {
            font-size: 0.76rem;
            font-weight: 700;
            padding: 5px 12px;
            border-radius: 999px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.06);
        }
        .pill-danger { background: #FEE2E2; color: #DC2626; border: 1px solid #FECACA; }
        .pill-warning { background: #FEF3C7; color: #D97706; border: 1px solid #FDE68A; }
        .pill-safe { background: #DCFCE7; color: #16A34A; border: 1px solid #BBF7D0; }

        .essential-amount-3d {
            font-size: 1.65rem;
            font-weight: 800;
            color: #0F172A;
            margin-bottom: 4px;
            transform: translateZ(45px);
        }
        .essential-limit-3d {
            font-size: 0.85rem;
            color: #64748B;
            margin-bottom: 14px;
            transform: translateZ(25px);
        }

        /* Thanh tiến độ 3D có hiệu ứng ánh sáng chạy qua (Shimmer Bar) */
        .progress-track-3d {
            width: 100%;
            height: 13px;
            background: #E2E8F0;
            border-radius: 999px;
            overflow: hidden;
            margin-bottom: 10px;
            box-shadow: inset 0 2px 4px rgba(15, 23, 42, 0.12);
            transform: translateZ(35px);
        }
        .progress-fill-3d {
            height: 100%;
            border-radius: 999px;
            position: relative;
            transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1);
            background-size: 200% 100%;
            animation: shimmerSweep 3.2s linear infinite;
        }

        /* ================= HỘP CẢNH BÁO 3D (PULSE ALERT BOXES) ================= */
        .alert-box-3d {
            border-radius: 16px;
            padding: 15px 20px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            font-size: 0.93rem;
            font-weight: 600;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }
        .alert-box-3d:hover {
            transform: translateY(-2px) scale(1.005);
        }
        .alert-danger-3d {
            background: linear-gradient(90deg, #FEF2F2 0%, #FFF5F5 100%);
            border-left: 6px solid #EF4444;
            color: #991B1B;
            border-top: 1px solid #FECACA;
            border-right: 1px solid #FECACA;
            border-bottom: 1px solid #FECACA;
            animation: pulseDanger3D 2.4s infinite;
        }
        .alert-warning-3d {
            background: linear-gradient(90deg, #FFFBEB 0%, #FEFCE8 100%);
            border-left: 6px solid #F59E0B;
            color: #92400E;
            border-top: 1px solid #FDE68A;
            border-right: 1px solid #FDE68A;
            border-bottom: 1px solid #FDE68A;
            box-shadow: 0 6px 18px rgba(245, 158, 11, 0.12);
        }
        .alert-safe-3d {
            background: linear-gradient(90deg, #F0FDF4 0%, #F7FEE7 100%);
            border-left: 6px solid #22C55E;
            color: #166534;
            border-top: 1px solid #BBF7D0;
            border-right: 1px solid #BBF7D0;
            border-bottom: 1px solid #BBF7D0;
            box-shadow: 0 6px 18px rgba(34, 197, 94, 0.1);
        }

        /* Section Titles */
        .section-heading-3d {
            font-size: 1.22rem;
            font-weight: 800;
            color: #1E293B;
            margin: 20px 0 14px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Nút bấm và Tabs tương tác 3D */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background: rgba(241, 245, 249, 0.9);
            backdrop-filter: blur(10px);
            padding: 8px;
            border-radius: 16px;
            box-shadow: inset 0 2px 5px rgba(15, 23, 42, 0.06);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px;
            padding: 10px 20px;
            font-weight: 700;
            font-size: 0.93rem;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .stTabs [data-baseweb="tab"]:hover {
            transform: translateY(-2px);
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 8px 20px -4px rgba(79, 70, 229, 0.45) !important;
            transform: translateY(-2px);
        }

        div.stButton > button {
            border-radius: 12px !important;
            font-weight: 700 !important;
            transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }
        div.stButton > button:hover {
            transform: translateY(-3px) scale(1.01) !important;
            box-shadow: 0 12px 24px -6px rgba(79, 70, 229, 0.4) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    theme_path = Path(__file__).with_name("theme.css")
    if theme_path.is_file():
        st.html(f"<style>{theme_path.read_text(encoding='utf-8')}</style>")

    # Nhúng JavaScript Engine gắn sự kiện di chuột 3D Tilt + Glare Spotlight cho tất cả thẻ 3D
    components.html("""
    <script>
    (function() {
        const parentDoc = window.parent.document;

        function bind3DTilt() {
            const cards = parentDoc.querySelectorAll('.kpi-card-3d, .essential-card-3d, .hero-banner-3d');
            cards.forEach(card => {
                if (card.dataset.tiltBound === "true") return;
                card.dataset.tiltBound = "true";

                // Tạo lớp ánh sáng phản chiếu 3D (Spotlight Glare)
                const glare = parentDoc.createElement('div');
                glare.style.position = 'absolute';
                glare.style.top = '0';
                glare.style.left = '0';
                glare.style.width = '100%';
                glare.style.height = '100%';
                glare.style.pointerEvents = 'none';
                glare.style.borderRadius = 'inherit';
                glare.style.transition = 'opacity 0.25s ease';
                glare.style.opacity = '0';
                glare.style.zIndex = '2';
                card.appendChild(glare);

                card.addEventListener('mousemove', (e) => {
                    const rect = card.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    const centerX = rect.width / 2;
                    const centerY = rect.height / 2;

                    // Tính góc nghiêng 3D theo vị trí con trỏ chuột
                    const maxTilt = card.classList.contains('hero-banner-3d') ? 4 : 9;
                    const rotateX = ((y - centerY) / centerY) * (-maxTilt);
                    const rotateY = ((x - centerX) / centerX) * maxTilt;

                    card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-5px) scale3d(1.015, 1.015, 1.015)`;
                    glare.style.opacity = '1';
                    glare.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(255,255,255,0.38) 0%, rgba(255,255,255,0) 65%)`;
                });

                card.addEventListener('mouseleave', () => {
                    card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px) scale3d(1, 1, 1)';
                    glare.style.opacity = '0';
                });
            });
        }

        // Gắn ngay khi tải và tự động gắn lại khi chuyển Tab trên Streamlit
        bind3DTilt();
        setInterval(bind3DTilt, 800);
    })();
    </script>
    """, height=0, width=0)


# =============================================================================
# 3. KHỞI TẠO KẾT NỐI TỚI BACKEND (backend.py)
# =============================================================================
@st.cache_resource
def get_backend() -> ExpenseBackend:
    """Khởi tạo đối tượng Backend liên kết với SQLite."""
    return ExpenseBackend("data/student_expense.db")


backend = get_backend()
inject_3d_styles_and_scripts()


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
    st.markdown("""
    <div style="text-align:center; padding: 14px 10px 18px 10px; background: linear-gradient(135deg, #1E1B4B 0%, #4338CA 100%); border-radius: 18px; color: white; margin-bottom: 18px; box-shadow: 0 10px 25px -6px rgba(67, 56, 202, 0.45);">
        <div style="font-size: 2.3rem; margin-bottom: 4px; animation: float3D 3.5s ease-in-out infinite;">🎓💳</div>
        <div style="font-size: 1.25rem; font-weight: 800; letter-spacing: -0.01em;">UniSpend 3D</div>
        <div style="font-size: 0.78rem; color: #C7D2FE;">Giao diện 3D Tương tác ↔ Backend</div>
    </div>
    """, unsafe_allow_html=True)

    available_months = backend.get_available_months()
    saved_month = st.session_state.pop("report_month_after_save", None)
    if saved_month in available_months:
        st.session_state["report_month"] = saved_month
    elif st.session_state.get("report_month") not in available_months:
        st.session_state["report_month"] = available_months[0]
    selected_month = st.selectbox(
        "📅 Chọn tháng xem báo cáo:",
        options=available_months,
        index=0,
        key="report_month",
        help="Chọn tháng để Backend tính toán thống kê Tiền ăn, Tiền trọ, Đi lại và cảnh báo ngân sách."
    )

    st.markdown("---")
    st.markdown("### ⚡ Nhập Khoản Thu / Chi Hằng Ngày")

    tx_type_quick = st.radio(
        "Loại giao dịch:",
        options=["Chi tiêu", "Thu nhập"],
        horizontal=True,
        key="sidebar_tx_type"
    )

    # Nút chọn nhanh mệnh giá tiền phổ biến của sinh viên (Interactive Quick Chips)
    st.caption("💡 Bấm chọn nhanh mệnh giá phổ biến:")
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
    with st.expander("🛠️ Công cụ Demo & Kiểm thử"):
        st.caption("Khôi phục dữ liệu mẫu 4 tháng để thuyết trình Bài tập lớn:")
        if st.button("🔄 Nạp lại dữ liệu mẫu", use_container_width=True):
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


# =============================================================================
# 6. BANNER 3D & THẺ VÍ SINH VIÊN LẬT 2 MẶT (3D FLIP STUDENT WALLET)
# =============================================================================
y_str, m_str = selected_month.split("-")
health_score = max(0, min(100, int(100 - max(0, budget_used_pct - 75) * 2)))
health_label = "Tốt 🌟" if budget_used_pct < 80 else ("Cần chú ý ⚠️" if budget_used_pct <= 100 else "Vượt định mức 🚨")

st.html(f"""
<div class="hero-3d-wrapper">
    <!-- Khối Banner 3D bên trái -->
    <div class="hero-banner-3d">
        <div class="orb-1"></div>
        <div class="orb-2"></div>
        <div>
            <div class="hero-tag">✨ Không Gian Tài Chính Sinh Viên 3D • Kỳ {m_str}/{y_str}</div>
            <div class="hero-title-3d">🎓 UniSpend — Quản Lý Chi Tiêu Sinh Viên</div>
            <p class="hero-desc-3d">
                Di chuột lên các thẻ để trải nghiệm <strong>hiệu ứng nghiêng 3D (3D Perspective Tilt)</strong>
                và rê chuột vào <strong>Thẻ Ví Sinh Viên bên phải để lật mặt sau 3D</strong> xem hạn mức chi tiêu mỗi ngày!
            </p>
        </div>
        <div class="hero-pills-row">
            <div class="hero-mini-pill">🍜 Tiền ăn: {format_vnd(essential_stats[0]['spent'])}</div>
            <div class="hero-mini-pill">🏠 Tiền trọ: {format_vnd(essential_stats[1]['spent'])}</div>
            <div class="hero-mini-pill">🛵 Đi lại: {format_vnd(essential_stats[2]['spent'])}</div>
            <div class="hero-mini-pill">🛡️ Sức khỏe ví: {health_label}</div>
        </div>
    </div>

    <!-- Thẻ Ví Sinh Viên Lật 3D (Hover để lật 180 độ) -->
    <div class="wallet-scene">
        <div class="wallet-card-3d">
            <!-- Mặt trước thẻ -->
            <div class="wallet-face wallet-front">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="chip-3d"></div>
                    <span class="flip-hint">🔄 Rê chuột để lật 3D</span>
                </div>
                <div>
                    <div style="font-size:0.76rem; text-transform:uppercase; letter-spacing:0.08em; opacity:0.85;">
                        Số dư khả dụng tháng {m_str}/{y_str}
                    </div>
                    <div style="font-size:1.85rem; font-weight:800; letter-spacing:-0.02em; margin-top:2px;">
                        {format_vnd(balance)}
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end; font-size:0.82rem;">
                    <div>
                        <div style="opacity:0.75; font-size:0.7rem;">CHỦ THẺ SINH VIÊN</div>
                        <div style="font-weight:700; letter-spacing:0.05em;">UNISPEND MEMBER • {y_str}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="opacity:0.75; font-size:0.7rem;">ĐÃ DÙNG NGÂN SÁCH</div>
                        <div style="font-weight:800;">{budget_used_pct:.1f}%</div>
                    </div>
                </div>
            </div>
            <!-- Mặt sau thẻ (Hiện khi lật 3D) -->
            <div class="wallet-face wallet-back">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.15); padding-bottom:8px;">
                    <span style="font-size:0.82rem; font-weight:700; color:#38BDF8;">📊 PHÂN TÍCH HẠN MỨC NHANH</span>
                    <span style="font-size:0.75rem; color:#94A3B8;">Tháng {m_str}/{y_str}</span>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; my:auto;">
                    <div style="background:rgba(255,255,255,0.06); padding:10px 12px; border-radius:12px;">
                        <div style="font-size:0.72rem; color:#94A3B8;">Ngân sách còn lại</div>
                        <div style="font-size:1.05rem; font-weight:800; color:#4ADE80;">{format_vnd(max(0, budget_remaining))}</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.06); padding:10px 12px; border-radius:12px;">
                        <div style="font-size:0.72rem; color:#94A3B8;">Gợi ý tiêu tối đa/ngày</div>
                        <div style="font-size:1.05rem; font-weight:800; color:#FBBF24;">{format_vnd(max(0, budget_remaining) / 15)}</div>
                    </div>
                </div>
                <div style="font-size:0.76rem; color:#CBD5E1; display:flex; justify-content:space-between;">
                    <span>Tổng giao dịch: <strong>{len(df_month)} khoản</strong></span>
                    <span>Điểm an toàn: <strong>{health_score}/100</strong></span>
                </div>
            </div>
        </div>
    </div>
</div>
""")


# =============================================================================
# 7. HỆ THỐNG CẢNH BÁO NGÂN SÁCH TỨC THỜI (3D PULSE ALERTS)
# =============================================================================
danger_alerts = [a for a in alerts if a["level"] == "danger"]
warning_alerts = [a for a in alerts if a["level"] == "warning"]

if danger_alerts or warning_alerts:
    for alert in danger_alerts:
        st.markdown(f"""
        <div class="alert-box-3d alert-danger-3d">
            <div>🚨 <strong>{alert['message']}</strong></div>
            <span style="font-size:0.76rem; background:#DC2626; color:white; padding:4px 12px; border-radius:99px; white-space:nowrap;">VƯỢT NGÂN SÁCH</span>
        </div>
        """, unsafe_allow_html=True)
    for alert in warning_alerts:
        st.markdown(f"""
        <div class="alert-box-3d alert-warning-3d">
            <div>⚠️ <strong>{alert['message']}</strong></div>
            <span style="font-size:0.76rem; background:#D97706; color:white; padding:4px 12px; border-radius:99px; white-space:nowrap;">SẮP CHẠM NGƯỠNG</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="alert-box-3d alert-safe-3d">
        <div>✅ <strong>Tuyệt vời! Chi tiêu tháng {m_str}/{y_str} đang nằm trong ngưỡng ngân sách an toàn.</strong></div>
        <span style="font-size:0.76rem; background:#16A34A; color:white; padding:4px 12px; border-radius:99px;">AN TOÀN</span>
    </div>
    """, unsafe_allow_html=True)


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
    bal_sub = "Số dư tích lũy còn lại" if balance >= 0 else "Chi vượt tổng thu nhập!"
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
tab_overview, tab_charts, tab_simulator, tab_ledger = st.tabs([
    "🍜 Thống Kê 3D: Tiền Ăn • Trọ • Đi Lại",
    "📊 Biểu Đồ Tương Tác Theo Tháng",
    "🎛️ Giả Lập Tương Tác & Cảnh Báo Ngân Sách",
    "📝 Sổ Giao Dịch Hằng Ngày (Thu/Chi)"
])


# -----------------------------------------------------------------------------
# TAB 1: THỐNG KÊ 3D TIỀN ĂN, TIỀN TRỌ, ĐI LẠI
# -----------------------------------------------------------------------------
with tab_overview:
    st.markdown('<div class="section-heading-3d">🔥 Thống kê 3 khoản chi tiêu trọng tâm: Tiền ăn • Tiền trọ • Đi lại (Nghiêng 3D khi rê chuột)</div>', unsafe_allow_html=True)

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
                <div style="font-size: 0.84rem; font-weight: 700; color: #334155; margin-bottom: 4px; transform: translateZ(20px);">
                    {item['note_text']}
                </div>
                <div style="font-size: 0.77rem; color: #94A3B8; transform: translateZ(15px);">{item['desc']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-heading-3d">📌 Bảng phân tích chi tiết & Biểu đồ tương tác cơ cấu chi tiêu</div>', unsafe_allow_html=True)
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
                .properties(height=320, title=f"Cơ cấu chi tiêu tháng {selected_month} (Rê chuột để tương tác)")
            )
            st.altair_chart(donut_chart, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu chi tiêu trong tháng này.")


# -----------------------------------------------------------------------------
# TAB 2: BIỂU ĐỒ CHI TIÊU THEO THÁNG (TƯƠNG TÁC ZOOM, FILTER, HOVER)
# -----------------------------------------------------------------------------
with tab_charts:
    st.markdown('<div class="section-heading-3d">📈 Biểu đồ Chi tiêu theo Tháng & Phân tích Xu hướng Tương tác</div>', unsafe_allow_html=True)

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
    st.markdown(f'<div class="section-heading-3d">📝 Sổ nhật ký Thu / Chi hằng ngày (Tháng {selected_month})</div>', unsafe_allow_html=True)

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
