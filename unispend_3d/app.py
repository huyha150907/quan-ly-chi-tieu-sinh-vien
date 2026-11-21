# -*- coding: utf-8 -*-
"""
Module app.py (UTH Spend — Giao diện đầy đủ 8 chức năng giống UniSpend 2.0 + Màu Tím-Xanh Băng + Hiệu ứng 3D)
-------------------------------------------------------------------------
Tích hợp đầy đủ 8 mục điều hướng giống mẫu https://thuvien01.streamlit.app/:
1. Lịch tài chính (Money Calendar 7 cột, 4 KPI Sparkline 3D, Chi tiêu an toàn, Quick Add)
2. Hóa đơn & Sổ nợ (Quản lý hóa đơn định kỳ & sổ nợ, đánh dấu đã thanh toán)
3. Kho ảnh hóa đơn (Lưu trữ & xem lại thư viện ảnh hóa đơn thực tế)
4. Thống kê chi tiêu (Tiền ăn • Tiền trọ • Đi lại, biểu đồ theo tháng, tỷ trọng)
5. AI Làm sạch dữ liệu (Tải CSV thô hoặc dán ghi chú lộn xộn -> tự tách khoản thu/chi)
6. Quét hóa đơn AI (Tải ảnh / Chụp Camera / Dán nội dung hóa đơn -> tự bóc số tiền & danh mục)
7. Nhập giọng nói (Ghi âm micro + nhập câu nói tiếng Việt -> tự phân tích & lưu sổ)
8. Cá nhân & Tài khoản (Cài đặt định mức ngân sách, Xuất/Nhập CSV rõ ràng, Sổ giao dịch)

Màu sắc: Tông sáng Xanh băng - Tím (#F5F8FF -> #E8EEFF, điểm nhấn Tím #6328E8) + Hiệu ứng 3D.
Liên kết 100% dữ liệu thật với `backend.py` & SQLite (`data/student_expense.db`).
"""

import base64
import calendar
import json
import os
import re
from csv import Error as CsvError
from datetime import date, datetime
from html import escape
from sqlite3 import Error as DatabaseError
from uuid import uuid4
from typing import Dict, List
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
# 1. CẤU HÌNH TRANG & THƯ MỤC LƯU TRỮ PHỤ TRỢ
# =============================================================================
st.set_page_config(
    page_title="UTH — Quản Lý Chi Tiêu Sinh Viên",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = database_path().parent
RECEIPTS_DIR = os.path.join(DATA_DIR, "receipts")
BILLS_FILE = os.path.join(DATA_DIR, "bills_debts.json")
RECEIPT_META_FILE = os.path.join(DATA_DIR, "receipts_meta.json")
os.makedirs(RECEIPTS_DIR, exist_ok=True)


def format_vnd(amount: float) -> str:
    return f"{amount:,.0f} đ".replace(",", ".")


def format_compact_vnd(amount: float) -> str:
    abs_a = abs(amount)
    sign = "-" if amount > 0 else ""
    if abs_a >= 1_000_000:
        return f"{sign}{abs_a / 1_000_000:.1f}tr".replace(".", ",")
    if abs_a >= 1_000:
        return f"{sign}{int(round(abs_a / 1_000))}k"
    return f"{sign}{int(abs_a)}đ"


# =============================================================================
# 2. BỘ PHÂN TÍCH NGÔN NGỮ TIẾNG VIỆT CHO GIỌNG NÓI / HÓA ĐƠN / LÀM SẠCH DỮ LIỆU
# =============================================================================
def parse_vietnamese_amount(text: str) -> float:
    """Bóc tách số tiền tiếng Việt từ câu nói/văn bản (VD: 45k, 1tr8, 1.5 triệu, 120.000đ)."""
    s = text.lower().replace(",", ".")
    # Dạng 1tr8, 2tr5
    m = re.search(r"(\d+)\s*(?:tr|triệu)\s*(\d+)", s)
    if m:
        whole = int(m.group(1))
        frac = m.group(2)
        return whole * 1_000_000 + int(frac) * (10 ** (6 - len(frac)))
    # Dạng 1.5tr, 2 triệu
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:tr|triệu)", s)
    if m:
        return float(m.group(1)) * 1_000_000
    # Dạng 45k, 50 nghìn, 50 ngàn
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:k|nghìn|ngàn|ng)", s)
    if m:
        return float(m.group(1)) * 1_000
    # Dạng số nguyên lớn có dấu chấm hoặc chữ đ/vnd: 120.000đ, 50000
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d{4,9})\s*(?:đ|d|vnd|vnđ)?", s)
    if m:
        return float(m.group(1).replace(".", ""))
    return 0.0


def classify_vietnamese_tx(text: str) -> tuple[str, str]:
    """Tự động nhận diện (Loại giao dịch, Danh mục) từ câu nói hoặc dòng hóa đơn."""
    s = text.lower()
    income_kw = ["lương", "trợ cấp", "bố mẹ", "ba mẹ", "học bổng", "thưởng", "lì xì", "thu nhập", "nhận tiền", "gia sư"]
    if any(k in s for k in income_kw):
        if any(k in s for k in ["bố mẹ", "ba mẹ", "trợ cấp", "gia đình"]):
            return "Thu nhập", "Trợ cấp gia đình"
        if any(k in s for k in ["học bổng", "thưởng"]):
            return "Thu nhập", "Học bổng & Thưởng"
        if any(k in s for k in ["lương", "gia sư", "làm thêm", "part-time", "thực tập"]):
            return "Thu nhập", "Làm thêm (Part-time)"
        return "Thu nhập", "Thu nhập khác"

    if any(k in s for k in ["trọ", "phòng", "điện", "nước", "wifi", "internet", "tiền nhà"]):
        return "Chi tiêu", "Tiền trọ"
    if any(k in s for k in ["xăng", "xe", "grab", "be", "buýt", "bus", "gửi xe", "sửa xe", "đi lại", "vé"]):
        return "Chi tiêu", "Đi lại"
    if any(k in s for k in ["sách", "giáo trình", "học phí", "in ấn", "photo", "tài liệu", "học tập", "vở", "bút"]):
        return "Chi tiêu", "Học tập"
    if any(k in s for k in ["ăn", "cơm", "phở", "bún", "bánh", "trà sữa", "cà phê", "cafe", "nước uống", "siêu thị", "chợ", "lẩu", "gà", "nhậu"]):
        return "Chi tiêu", "Tiền ăn"
    if any(k in s for k in ["quần", "áo", "giày", "mua sắm", "bột giặt", "dầu gội", "đồ dùng", "shopee"]):
        return "Chi tiêu", "Sinh hoạt & Mua sắm"
    if any(k in s for k in ["phim", "cgv", "game", "sinh nhật", "quà", "giải trí", "karaoke", "bạn bè"]):
        return "Chi tiêu", "Giải trí & Xã giao"
    return "Chi tiêu", "Chi phí khác"


def parse_raw_notes_to_rows(raw_text: str) -> List[Dict]:
    """Tách nhiều dòng/câu ghi chú thô thành danh sách giao dịch chuẩn."""
    chunks = re.split(r"[\n,;]+", raw_text)
    rows = []
    today_str = date.today().strftime("%Y-%m-%d")
    for ch in chunks:
        c = ch.strip()
        if not c:
            continue
        amt = parse_vietnamese_amount(c)
        if amt <= 0:
            continue
        tx_type, cat = classify_vietnamese_tx(c)
        # Tìm ngày dạng dd/mm/yyyy hoặc dd/mm
        dt_str = today_str
        m_dt = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", c)
        if m_dt:
            d_v, m_v = int(m_dt.group(1)), int(m_dt.group(2))
            y_v = int(m_dt.group(3)) if m_dt.group(3) else date.today().year
            if y_v < 100:
                y_v += 2000
            try:
                dt_str = date(y_v, m_v, d_v).strftime("%Y-%m-%d")
            except ValueError:
                dt_str = today_str
        rows.append({
            "date": dt_str,
            "tx_type": tx_type,
            "category": cat,
            "amount": amt,
            "note": c
        })
    return rows


# =============================================================================
# 3. QUẢN LÝ JSON LƯU HÓA ĐƠN ĐỊNH KỲ / SỔ NỢ & KHO ẢNH HÓA ĐƠN
# =============================================================================
def load_bills() -> List[Dict]:
    if os.path.exists(BILLS_FILE):
        with open(BILLS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    default_bills = [
        {"id": 1, "kind": "Định kỳ", "title": "Tiền thuê phòng trọ tháng này", "category": "Tiền trọ", "amount": 1850000, "due": "25/11/2026", "paid": False},
        {"id": 2, "kind": "Định kỳ", "title": "Tiền mạng Wifi & Rác", "category": "Tiền trọ", "amount": 120000, "due": "28/11/2026", "paid": False},
        {"id": 3, "kind": "Sổ nợ", "title": "Ứng tiền in báo cáo nhóm Python (Bạn Minh)", "category": "Học tập", "amount": 85000, "due": "22/11/2026", "paid": False},
        {"id": 4, "kind": "Định kỳ", "title": "Vé gửi xe tháng tại trường UTH", "category": "Đi lại", "amount": 60000, "due": "05/11/2026", "paid": True},
    ]
    save_bills(default_bills)
    return default_bills


def save_bills(items: List[Dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(BILLS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def load_receipts_meta() -> List[Dict]:
    if os.path.exists(RECEIPT_META_FILE):
        with open(RECEIPT_META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_receipts_meta(items: List[Dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RECEIPT_META_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


# =============================================================================
# 4. CSS TÔNG SÁNG XANH BĂNG - TÍM (#6328E8) + HIỆU ỨNG ĐỘNG & 3D ENGINE
# =============================================================================
def inject_uth_3d_theme(is_dark: bool):
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

        [data-testid="InputInstructions"] {{ display: none !important; }}

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--text-main);
        }}

        .stApp {{ background: {app_bg_css}; }}

        section[data-testid="stSidebar"] {{
            background-color: var(--bg-sidebar) !important;
            border-right: 1px solid var(--border-col) !important;
        }}

        header[data-testid="stHeader"] {{ background: transparent !important; }}

        .block-container {{
            padding-top: 1.1rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 1420px !important;
            perspective: 1400px;
        }}

        @keyframes slideUp3D {{
            from {{ opacity: 0; transform: perspective(1000px) translateY(16px) rotateX(-5deg); }}
            to {{ opacity: 1; transform: perspective(1000px) translateY(0) rotateX(0deg); }}
        }}
        @keyframes float3D {{
            0%, 100% {{ transform: translate3d(0, 0px, 0) rotateY(-3deg); }}
            50% {{ transform: translate3d(0, -7px, 14px) rotateY(3deg); }}
        }}
        @keyframes pulsePurple {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(99, 40, 232, 0.42); }}
            50% {{ box-shadow: 0 0 0 8px rgba(99, 40, 232, 0); }}
        }}
        @keyframes pulseDanger {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.35); }}
            50% {{ box-shadow: 0 0 0 7px rgba(239, 68, 68, 0); }}
        }}
        @keyframes shimmerBar {{
            0% {{ background-position: -200% 0; }}
            100% {{ background-position: 200% 0; }}
        }}

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
            box-shadow: 0 8px 24px -10px rgba(99, 40, 232, 0.16);
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
        .kpi-3d-card.danger-border {{ border-color: var(--red-border); }}

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

        .cal-header-row {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
            text-align: center;
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
            margin: 8px 0;
        }}
        .cal-grid {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
        }}
        .cal-cell {{
            border-radius: 14px;
            padding: 8px 6px;
            min-height: 62px;
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
        .cal-cell.high-spend {{ background: var(--red-bg); border-color: var(--red-border); }}
        .cal-cell.mid-spend {{ background: var(--amber-bg); border-color: var(--amber-border); }}
        .cal-cell.today-cell {{ border: 2px solid var(--accent); animation: pulsePurple 2.4s infinite; }}
        .cal-cell.empty-cell {{ background: transparent; border-color: transparent; }}
        .cal-day-num {{ font-size: 14px; font-weight: 700; color: var(--text-main); }}
        .cal-day-amt {{ font-size: 11px; font-weight: 700; margin-top: 3px; }}

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

        .mic-pulse-ring {{
            width: 84px;
            height: 84px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6328E8 0%, #EC4899 100%);
            color: #FFFFFF;
            font-size: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 10px auto 14px auto;
            animation: pulsePurple 2s infinite;
        }}
    </style>
    """)

    # JavaScript 3D Tilt + Spotlight Glare tím theo con trỏ chuột
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
    path = "M 2 24 Q 25 22, 45 14 T 88 4" if trend_up else "M 2 18 Q 28 22, 48 16 T 88 12"
    return f'<svg width="86" height="28" viewBox="0 0 90 28" fill="none"><path d="{path}" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/></svg>'


# =============================================================================
# 5. KẾT NỐI BACKEND & KHỞI TẠO TRẠNG THÁI
# =============================================================================
@st.cache_resource
def get_backend(path: str) -> ExpenseBackend:
    return ExpenseBackend(path)


backend = get_backend(str(database_path()))
available_months = backend.get_available_months()

NAV_ITEMS = [
    "Lịch tài chính",
    "Hóa đơn & Sổ nợ",
    "Kho ảnh hóa đơn",
    "Thống kê chi tiêu",
    "AI Làm sạch dữ liệu",
    "Quét hóa đơn AI",
    "Nhập giọng nói",
    "Cá nhân & Tài khoản",
]
NAV_ICONS = {
    "Lịch tài chính": "📅",
    "Hóa đơn & Sổ nợ": "🧾",
    "Kho ảnh hóa đơn": "🖼️",
    "Thống kê chi tiêu": "📊",
    "AI Làm sạch dữ liệu": "✨",
    "Quét hóa đơn AI": "📷",
    "Nhập giọng nói": "🎙️",
    "Cá nhân & Tài khoản": "👤",
}

if "is_dark" not in st.session_state:
    st.session_state.is_dark = False
if st.session_state.get("selected_month") not in available_months:
    st.session_state.selected_month = available_months[0]
if pending_page := st.session_state.pop("pending_nav_page", None):
    st.session_state["sidebar_nav_radio"] = pending_page
if "selected_day" not in st.session_state:
    st.session_state.selected_day = date.today().strftime("%Y-%m-%d")
if "voice_text_val" not in st.session_state:
    st.session_state.voice_text_val = ""

inject_uth_3d_theme(st.session_state.is_dark)

selected_month = st.session_state.selected_month
y_int, m_int = map(int, selected_month.split("-"))

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
days_left = max(1, days_in_month - today_obj.day + 1) if (y_int == today_obj.year and m_int == today_obj.month) else days_in_month
safe_daily = max(0.0, budget_remaining) / days_left


# =============================================================================
# 6. SIDEBAR ĐẦY ĐỦ 8 MỤC ĐIỀU HƯỚNG GIỐNG MẪU THUVIEN01
# =============================================================================
with st.sidebar:
    st.html("""
    <div style="display:flex; align-items:center; gap:12px; padding:6px 4px 16px 4px; border-bottom:1px solid var(--border-col); margin-bottom:14px;">
        <div style="width:44px; height:44px; border-radius:12px; background:var(--accent-soft); border:1px solid rgba(99,40,232,0.35); display:flex; align-items:center; justify-content:center; font-size:22px;">🐷</div>
        <div>
            <div style="font-size:19px; font-weight:900; background:linear-gradient(135deg,#6328E8,#EC4899); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">UTH Spend</div>
            <div style="font-size:11.5px; color:var(--text-muted);">Quản lý chi tiêu sinh viên</div>
        </div>
    </div>
    <div style="font-size:11px; font-weight:700; letter-spacing:0.06em; color:var(--text-muted); margin-bottom:8px;">ĐIỀU HƯỚNG CHÍNH</div>
    """)

    st.session_state.nav_page = st.radio(
        "Điều hướng chính",
        options=NAV_ITEMS,
        format_func=lambda x: f"{NAV_ICONS[x]}  {x}",
        label_visibility="collapsed",
        key="sidebar_nav_radio"
    )

    st.markdown("---")
    tip_text = (
        f"Có thể chi an toàn <strong>{format_vnd(safe_daily)}/ngày</strong> trong {days_left} ngày tới."
        if budget_remaining >= 0
        else f"Đã vượt định mức tháng <strong>{format_vnd(abs(budget_remaining))}</strong>. Ưu tiên khoản thiết yếu!"
    )
    st.html(f"""
    <div style="background:var(--accent-soft); border:1px solid rgba(99,40,232,0.35); border-radius:14px; padding:14px; margin-bottom:14px;">
        <div style="font-size:12.5px; font-weight:700; color:var(--accent); margin-bottom:6px;">✨ Gợi ý từ UTH AI</div>
        <div style="font-size:12.5px; color:var(--text-main); line-height:1.45;">{tip_text}</div>
    </div>
    """)

    theme_lbl = "☀️ Chuyển Light Mode" if st.session_state.is_dark else "🌙 Chuyển Dark Mode"
    if st.button(theme_lbl, use_container_width=True):
        st.session_state.is_dark = not st.session_state.is_dark
        st.rerun()

    st.caption(f"Tháng {selected_month} · SQLite3 ({len(df_month)} GD)")


# =============================================================================
# 7. TOP HEADER BAR (GIỐNG MẪU: THÁNG, HÔM NAY, QUÉT HÓA ĐƠN, GIỌNG NÓI)
# =============================================================================
h_left, h_prev, h_mlbl, h_next, h_today, h_ocr, h_voice = st.columns([2.9, 0.38, 1.15, 0.38, 0.78, 1.15, 0.95])

with h_left:
    titles_map = {
        "Lịch tài chính": ("Tổng quan tài chính", "Sinh viên UTH · Quản lý chi tiêu thông minh hơn nhé!"),
        "Hóa đơn & Sổ nợ": ("Hóa đơn & Sổ nợ", "Theo dõi tiền trọ, điện nước định kỳ và sổ vay/mượn bạn bè."),
        "Kho ảnh hóa đơn": ("Kho ảnh hóa đơn", "Lưu trữ và tra cứu toàn bộ ảnh biên lai, hóa đơn chi tiêu."),
        "Thống kê chi tiêu": ("Thống kê chi tiêu", "Phân tích Tiền ăn • Tiền trọ • Đi lại và biểu đồ theo tháng."),
        "AI Làm sạch dữ liệu": ("AI Làm sạch dữ liệu thô", "Tải file CSV thô hoặc dán ghi chú nhanh để tự động chuẩn hóa."),
        "Quét hóa đơn AI": ("Quét hóa đơn AI", "Tải ảnh, chụp camera hoặc dán văn bản hóa đơn để tự bóc tách."),
        "Nhập giọng nói": ("Nhập chi tiêu bằng Giọng nói", "Ghi âm hoặc đọc nhanh câu nói để tự động ghi nhận khoản chi."),
        "Cá nhân & Tài khoản": ("Cá nhân, Ngân sách & Sổ CSV", "Cài đặt định mức tháng, xem sổ đầy đủ và Xuất/Nhập CSV."),
    }
    pt, ps = titles_map[st.session_state.nav_page]
    st.html(f"""
    <div style="font-size:28px; font-weight:800; letter-spacing:-0.02em; color:var(--text-main);">{pt}</div>
    <div style="font-size:13px; color:var(--text-muted); margin-top:2px;">{ps}</div>
    """)

idx_m = available_months.index(selected_month)
with h_prev:
    st.write("")
    if st.button("‹", use_container_width=True, help="Tháng trước"):
        if idx_m + 1 < len(available_months):
            st.session_state.selected_month = available_months[idx_m + 1]
            st.rerun()
with h_mlbl:
    st.write("")
    st.html(f'<div style="text-align:center; padding:8px 6px; border-radius:10px; border:1px solid var(--border-col); background:var(--bg-card); font-weight:700; font-size:13px;">Tháng {m_int:02d}, {y_int}</div>')
with h_next:
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
with h_ocr:
    st.write("")
    if st.button("📷 Quét hóa đơn", type="primary", use_container_width=True):
        st.session_state.pending_nav_page = "Quét hóa đơn AI"
        st.rerun()
with h_voice:
    st.write("")
    if st.button("🎙️ Giọng nói", use_container_width=True):
        st.session_state.pending_nav_page = "Nhập giọng nói"
        st.rerun()

# Thanh trạng thái tài khoản & nút mở nhanh AI Làm sạch dữ liệu
strip_l, strip_r = st.columns([3.8, 1.2])
with strip_l:
    st.html(f"""
    <div class="account-strip" style="margin-bottom: 10px;">
        <div style="font-size:13.5px; font-weight:600; color:var(--text-main);">
            👤 Tài khoản: <span style="color:var(--accent); font-weight:700;">Sinh viên UTH (student_expense.db)</span>
            <span style="color:var(--text-muted); font-weight:500;"> · {len(df_month)} giao dịch · Tháng {selected_month}</span>
        </div>
        <div style="font-size:12px; font-weight:700; color:var(--accent); background:var(--accent-soft); padding:4px 12px; border-radius:99px;">
            SQLite3 Backend Active
        </div>
    </div>
    """)
with strip_r:
    st.write("")
    if st.button("✨ AI Làm sạch dữ liệu thô", type="primary", use_container_width=True):
        st.session_state.pending_nav_page = "AI Làm sạch dữ liệu"
        st.rerun()


# =============================================================================
# 8. HÀM DÙNG CHUNG: 4 THẺ KPI VỚI SPARKLINE MINI & HIỆU ỨNG 3D
# =============================================================================
def render_kpi_row():
    k1, k2, k3, k4 = st.columns(4)
    bal_col = "#6328E8" if balance >= 0 else "#DC2626"
    tx_exp_cnt = len(df_month[df_month["tx_type"] == "Chi tiêu"]) if not df_month.empty else 0
    is_over = budget_remaining < 0
    k4_cls = "kpi-3d-card danger-border" if is_over else "kpi-3d-card"
    k4_sub = f"Vượt {format_vnd(abs(budget_remaining))}" if is_over else f"Còn {format_vnd(budget_remaining)}"
    k4_sub_col = "#DC2626" if is_over else "#16A34A"

    with k1:
        st.html(f"""
        <div class="kpi-3d-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-size:13px; color:var(--text-muted); font-weight:600;">Số dư khả dụng</span>
                <span style="width:32px; height:32px; border-radius:9px; background:var(--accent-soft); color:var(--accent); display:flex; align-items:center; justify-content:center;">💳</span>
            </div>
            <div style="font-size:23px; font-weight:800; color:{bal_col}; margin-bottom:8px;">{format_vnd(balance)}</div>
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
            <div style="font-size:23px; font-weight:800; color:#16A34A; margin-bottom:8px;">+{format_vnd(total_income)}</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <span style="font-size:12px; color:var(--text-muted);">Nguồn thu trong tháng</span>
                {sparkline_svg("#16A34A", trend_up=True)}
            </div>
        </div>
        """)
    with k3:
        st.html(f"""
        <div class="kpi-3d-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-size:13px; color:var(--text-muted); font-weight:600;">Tổng chi tiêu</span>
                <span style="width:32px; height:32px; border-radius:9px; background:var(--red-bg); color:#DC2626; display:flex; align-items:center; justify-content:center;">↗</span>
            </div>
            <div style="font-size:23px; font-weight:800; color:#DC2626; margin-bottom:8px;">-{format_vnd(total_expense)}</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <span style="font-size:12px; color:var(--text-muted);">{tx_exp_cnt} giao dịch đã ghi</span>
                {sparkline_svg("#DC2626", trend_up=False)}
            </div>
        </div>
        """)
    with k4:
        st.html(f"""
        <div class="{k4_cls}">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-size:13px; color:var(--text-muted); font-weight:600;">Có thể chi hôm nay</span>
                <span style="width:32px; height:32px; border-radius:9px; background:{'var(--red-bg)' if is_over else 'var(--accent-soft)'}; color:{k4_sub_col}; display:flex; align-items:center; justify-content:center;">{'⚠️' if is_over else '🛡️'}</span>
            </div>
            <div style="font-size:23px; font-weight:800; color:var(--text-main); margin-bottom:8px;">{format_vnd(safe_daily)}</div>
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; font-weight:700; color:{k4_sub_col};">
                <span>{k4_sub}</span>
                <span>{budget_used_pct:.1f}%</span>
            </div>
        </div>
        """)
    st.write("")


# =============================================================================
# TRANG 1: LỊCH TÀI CHÍNH (MONEY CALENDAR)
# =============================================================================
if st.session_state.nav_page == "Lịch tài chính":
    render_kpi_row()
    cal_left, cal_right = st.columns([1.85, 1.0], gap="large")

    daily_exp_map = {}
    if not df_month.empty:
        daily_exp_map = df_month[df_month["tx_type"] == "Chi tiêu"].groupby("date")["amount"].sum().to_dict()

    with cal_left:
        st.html(f"""
        <div style="font-size:13px; font-weight:800; letter-spacing:0.06em; color:var(--text-muted); margin-bottom:10px;">
            🔥 LỊCH TÀI CHÍNH — THÁNG {m_int:02d}/{y_int}
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
            <div class="summary-chi-box">
                <div style="font-size:11.5px; font-weight:700; color:#DC2626;">↗ CHI THÁNG NÀY</div>
                <div style="font-size:23px; font-weight:800; color:#DC2626; margin-top:4px;">{format_vnd(total_expense)}</div>
            </div>
            <div class="summary-thu-box">
                <div style="font-size:11.5px; font-weight:700; color:#6328E8;">↙ THU THÁNG NÀY</div>
                <div style="font-size:23px; font-weight:800; color:#6328E8; margin-top:4px;">+{format_vnd(total_income)}</div>
            </div>
        </div>
        """)

        first_wd, num_days = calendar.monthrange(y_int, m_int)
        cells_html = '<div class="cal-cell empty-cell"></div>' * first_wd
        for d_num in range(1, num_days + 1):
            d_key = f"{y_int:04d}-{m_int:02d}-{d_num:02d}"
            spent_d = float(daily_exp_map.get(d_key, 0.0))
            is_today = (d_key == date.today().strftime("%Y-%m-%d"))
            cls_list = ["cal-cell"]
            if spent_d >= 500_000:
                cls_list.append("high-spend")
                amt_col = "#DC2626"
            elif spent_d > 0:
                cls_list.append("mid-spend")
                amt_col = "#D97706"
            else:
                amt_col = "var(--text-muted)"
            if is_today:
                cls_list.append("today-cell")
            amt_str = format_compact_vnd(spent_d) if spent_d > 0 else "—"
            cells_html += f'<div class="{" ".join(cls_list)}"><div class="cal-day-num">{d_num}</div><div class="cal-day-amt" style="color:{amt_col};">{amt_str}</div></div>'

        st.html(f"""
        <div class="glass-panel">
            <div class="cal-header-row"><div>T2</div><div>T3</div><div>T4</div><div>T5</div><div>T6</div><div>T7</div><div>CN</div></div>
            <div class="cal-grid">{cells_html}</div>
        </div>
        """)

        # Hộp Chi tiêu an toàn
        pct_bar = min(budget_used_pct, 100.0)
        bar_grad = (
            "linear-gradient(90deg, #EF4444, #F87171, #EF4444)" if budget_used_pct > 100
            else ("linear-gradient(90deg, #F59E0B, #FBBF24, #F59E0B)" if budget_used_pct >= 80 else "linear-gradient(90deg, #6328E8, #EC4899, #6328E8)")
        )
        status_pill = f"Vượt định mức (+{budget_used_pct - 100:.1f}%)" if budget_used_pct > 100 else ("Sắp chạm ngưỡng" if budget_used_pct >= 80 else "Trong vùng an toàn")
        status_col = "#DC2626" if budget_used_pct > 100 else ("#D97706" if budget_used_pct >= 80 else "#16A34A")

        danger_html = "".join(
            f'<div style="font-size:12.5px; color:{"#DC2626" if a["level"]=="danger" else "#D97706"}; margin-top:5px;">• {a["message"]}</div>'
            for a in alerts if a["level"] in ("danger", "warning")
        ) or '<div style="font-size:12.5px; color:#16A34A; margin-top:5px;">• Tất cả hạng mục đều nằm trong định mức cho phép.</div>'

        st.html(f"""
        <div class="glass-panel" style="border-color:{status_col};">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:15px; font-weight:700;">🛡️ Chi tiêu an toàn</span>
                <span style="font-size:11.5px; font-weight:700; padding:4px 10px; border-radius:99px; background:var(--red-bg); color:{status_col};">{status_pill}</span>
            </div>
            <div style="font-size:25px; font-weight:800;">{format_vnd(safe_daily)} <span style="font-size:14px; color:var(--text-muted); font-weight:500;">/ ngày</span></div>
            <div class="progress-track"><div class="progress-fill-shimmer" style="width:{pct_bar:.1f}%; background-image:{bar_grad};"></div></div>
            <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-muted); margin-bottom:10px;">
                <span>Đã chi tháng này: <strong>{format_vnd(total_expense)}</strong></span>
                <span>Định mức: <strong>{format_vnd(total_budget)} ({budget_used_pct:.1f}%)</strong></span>
            </div>
            <div style="background:var(--bg-card-2); border:1px solid var(--border-col); border-radius:12px; padding:12px 14px;">
                <div style="font-size:11.5px; font-weight:700; color:{status_col};">BÁO CÁO CẢNH BÁO NGÂN SÁCH</div>
                {danger_html}
            </div>
        </div>
        """)

    with cal_right:
        wallet_img_path = os.path.join(BASE_DIR, "assets", "wallet_3d.jpg")
        img_tag = ""
        if os.path.exists(wallet_img_path):
            with open(wallet_img_path, "rb") as f_img:
                b64_img = base64.b64encode(f_img.read()).decode("utf-8")
            img_tag = f'<img src="data:image/jpeg;base64,{b64_img}" class="float-3d-img" style="width:92px; height:92px; border-radius:16px; object-fit:cover;" />'

        st.html(f"""
        <div class="glass-panel" style="background:linear-gradient(135deg, var(--accent-soft) 0%, var(--bg-card) 100%); border-color:rgba(99,40,232,0.35);">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
                <div>
                    <div style="font-size:13px; font-weight:700; color:var(--accent); margin-bottom:6px;">✨ Gợi ý từ UTH AI</div>
                    <div style="font-size:13.5px; color:var(--text-main); line-height:1.45;">{tip_text}</div>
                </div>
                {img_tag}
            </div>
        </div>
        """)

        picked_day = st.date_input("📅 Xem giao dịch theo ngày:", value=date.fromisoformat(st.session_state.selected_day), key="finance_day")
        picked_str = picked_day.strftime("%Y-%m-%d")
        st.session_state.selected_day = picked_str
        df_day = df_month[df_month["date"] == picked_str] if not df_month.empty else pd.DataFrame()
        day_total = float(df_day[df_day["tx_type"] == "Chi tiêu"]["amount"].sum()) if not df_day.empty else 0.0

        day_rows_html = ""
        if not df_day.empty:
            for _, r in df_day.iterrows():
                col_r = "#DC2626" if r["tx_type"] == "Chi tiêu" else "#16A34A"
                sign_r = "-" if r["tx_type"] == "Chi tiêu" else "+"
                day_rows_html += f'<div style="display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid var(--border-col); font-size:13px;"><span>{escape(str(r["category"]))} · <span style="color:var(--text-muted);">{escape(str(r["note"]))}</span></span><strong style="color:{col_r};">{sign_r}{format_vnd(r["amount"])}</strong></div>'
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

        recent_html = ""
        if not df_month.empty:
            for _, r in df_month.head(6).iterrows():
                is_exp = r["tx_type"] == "Chi tiêu"
                amt_c = "#DC2626" if is_exp else "#16A34A"
                sgn = "-" if is_exp else "+"
                d_fmt = datetime.strptime(r["date"], "%Y-%m-%d").strftime("%d/%m")
                recent_html += f'<div style="display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:1px solid var(--border-col);"><div><div style="font-size:13.5px; font-weight:600;">{escape(str(r["note"]))}</div><div style="font-size:11.5px; color:var(--text-muted);">{d_fmt} · {escape(str(r["category"]))}</div></div><div style="font-size:13.5px; font-weight:700; color:{amt_c}; white-space:nowrap;">{sgn}{format_vnd(r["amount"])}</div></div>'
        else:
            recent_html = '<div style="font-size:13px; color:var(--text-muted);">Chưa có giao dịch nào.</div>'

        st.html(f'<div class="glass-panel"><div style="font-size:14px; font-weight:700; margin-bottom:6px;">🕒 Giao dịch gần đây</div>{recent_html}</div>')

    if notice := st.session_state.pop("quick_add_notice", None):
        st.success(notice)
    if st.session_state.pop("clear_quick_add", False):
        st.session_state.pop("qa_amt", None)
        st.session_state.pop("qa_note", None)

    # Quick Add + Phím tắt Camera / Kho ảnh / Giọng nói giống mẫu thuvien01
    with st.expander(f"⚡ Quick Add — Ghi nhanh ngày {picked_day.strftime('%d/%m/%Y')}", expanded=False):
        qa1, qa2, qa3, qa4, qa5 = st.columns([1, 1.2, 1.1, 1.6, 1])
        with qa1:
            qa_type = st.selectbox("Loại:", ["Chi tiêu", "Thu nhập"], key="qa_type")
        with qa2:
            qa_cats = backend.get_categories(qa_type)
            qa_cat = st.selectbox("Danh mục:", list(qa_cats.keys()), format_func=lambda c: f"{qa_cats[c]['icon']} {c}", key="qa_cat")
        with qa3:
            qa_amt = st.number_input("Số tiền (đ):", min_value=0, max_value=500_000_000, value=35_000, step=5_000, key="qa_amt")
        with qa4:
            qa_note = st.text_input("Ghi chú:", placeholder="VD: Cơm trưa, Đổ xăng...", key="qa_note")
        with qa5:
            st.write("")
            if st.button("💾 Lưu ngay", type="primary", use_container_width=True, key="qa_btn"):
                ok, msg = backend.add_daily_transaction(picked_str, qa_type, qa_cat, float(qa_amt), qa_note)
                if ok:
                    st.session_state.selected_month = picked_str[:7]
                    st.session_state["quick_add_notice"] = msg
                    st.session_state["clear_quick_add"] = True
                    st.rerun()
                else:
                    st.error(msg)

    with st.expander("🚀 Phím tắt Camera / Thư viện ảnh hóa đơn / Giọng nói", expanded=False):
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            if st.button("📷 Mở Quét hóa đơn AI", use_container_width=True):
                st.session_state.pending_nav_page = "Quét hóa đơn AI"
                st.rerun()
        with sc2:
            if st.button("🖼️ Mở Kho ảnh hóa đơn", use_container_width=True):
                st.session_state.pending_nav_page = "Kho ảnh hóa đơn"
                st.rerun()
        with sc3:
            if st.button("🎙️ Mở Nhập giọng nói", use_container_width=True):
                st.session_state.pending_nav_page = "Nhập giọng nói"
                st.rerun()


# =============================================================================
# TRANG 2: HÓA ĐƠN & SỔ NỢ
# =============================================================================
elif st.session_state.nav_page == "Hóa đơn & Sổ nợ":
    bills = load_bills()
    b_mode = st.radio("Chế độ xem:", ["Định kỳ", "Sổ nợ", "Tất cả"], horizontal=True)
    filtered_bills = bills if b_mode == "Tất cả" else [b for b in bills if b["kind"] == b_mode]

    unpaid_sum = sum(b["amount"] for b in filtered_bills if not b["paid"])
    paid_sum = sum(b["amount"] for b in filtered_bills if b["paid"])

    bm1, bm2 = st.columns(2)
    with bm1:
        st.html(f'<div class="summary-chi-box"><div style="font-size:12px; font-weight:700; color:#DC2626;">CHƯA THANH TOÁN</div><div style="font-size:26px; font-weight:800; color:#DC2626; margin-top:4px;">{format_vnd(unpaid_sum)}</div></div>')
    with bm2:
        st.html(f'<div class="summary-thu-box"><div style="font-size:12px; font-weight:700; color:#6328E8;">ĐÃ THANH TOÁN</div><div style="font-size:26px; font-weight:800; color:#6328E8; margin-top:4px;">{format_vnd(paid_sum)}</div></div>')

    st.write("")
    bl_col, br_col = st.columns([1.45, 1], gap="large")
    with bl_col:
        st.markdown("#### 📋 Danh sách Hóa đơn & Sổ nợ")
        if not filtered_bills:
            st.info("Chưa có hóa đơn hoặc khoản nợ nào trong mục này.")
        for b in filtered_bills:
            c_info, c_act = st.columns([3, 1.3])
            with c_info:
                badge = "✅ Đã trả" if b["paid"] else "⏳ Chưa trả"
                b_col = "#16A34A" if b["paid"] else "#DC2626"
                st.html(f"""
                <div class="glass-panel" style="padding:14px 18px; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-size:15px; font-weight:700;">{escape(str(b['title']))}</div>
                            <div style="font-size:12px; color:var(--text-muted);">{b['kind']} · {escape(str(b['category']))} · Hạn: {b['due']}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:16px; font-weight:800; color:#6328E8;">{format_vnd(b['amount'])}</div>
                            <div style="font-size:11.5px; font-weight:700; color:{b_col};">{badge}</div>
                        </div>
                    </div>
                </div>
                """)
            with c_act:
                st.write("")
                if not b["paid"]:
                    if st.button("✅ Đánh dấu đã trả", key=f"pay_bill_{b['id']}", type="primary", use_container_width=True):
                        for item in bills:
                            if item["id"] == b["id"]:
                                item["paid"] = True
                        save_bills(bills)
                        backend.add_daily_transaction(date.today().strftime("%Y-%m-%d"), "Chi tiêu", b["category"], float(b["amount"]), f"Thanh toán: {b['title']}")
                        st.toast("Đã đánh dấu thanh toán & ghi vào sổ chi tiêu!", icon="💜")
                        st.rerun()
                else:
                    if st.button("🗑️ Xóa", key=f"del_bill_{b['id']}", use_container_width=True):
                        bills = [x for x in bills if x["id"] != b["id"]]
                        save_bills(bills)
                        st.rerun()

    with br_col:
        st.markdown("#### ➕ Thêm Hóa đơn định kỳ / Sổ nợ mới")
        with st.form("add_bill_form", clear_on_submit=True):
            nb_kind = st.selectbox("Phân loại:", ["Định kỳ", "Sổ nợ"])
            nb_title = st.text_input("Tên hóa đơn / Khoản nợ:", placeholder="VD: Tiền điện tháng 11, Mượn bạn An...")
            nb_cat = st.selectbox("Danh mục:", list(EXPENSE_CATEGORIES.keys()))
            nb_amt = st.number_input("Số tiền (VNĐ):", min_value=1000, max_value=100_000_000, value=200_000, step=10_000)
            nb_due = st.date_input("Hạn thanh toán:", value=date.today())
            if st.form_submit_button("💾 Lưu hóa đơn", type="primary", use_container_width=True):
                if nb_title.strip():
                    new_id = max([x["id"] for x in bills], default=0) + 1
                    bills.append({
                        "id": new_id, "kind": nb_kind, "title": nb_title.strip(),
                        "category": nb_cat, "amount": float(nb_amt),
                        "due": nb_due.strftime("%d/%m/%Y"), "paid": False
                    })
                    save_bills(bills)
                    st.toast("Đã thêm hóa đơn mới!", icon="💜")
                    st.rerun()


# =============================================================================
# TRANG 3: KHO ẢNH HÓA ĐƠN
# =============================================================================
elif st.session_state.nav_page == "Kho ảnh hóa đơn":
    receipts = load_receipts_meta()
    total_rec_amt = sum(float(r.get("amount", 0)) for r in receipts)
    rm1, rm2 = st.columns(2)
    with rm1:
        st.html(f'<div class="kpi-3d-card"><div style="font-size:12px; color:var(--text-muted); font-weight:700;">SỐ ẢNH HÓA ĐƠN ĐÃ LƯU</div><div style="font-size:28px; font-weight:800; color:#6328E8;">{len(receipts)} ảnh</div></div>')
    with rm2:
        st.html(f'<div class="kpi-3d-card"><div style="font-size:12px; color:var(--text-muted); font-weight:700;">TỔNG GIÁ TRỊ HÓA ĐƠN</div><div style="font-size:28px; font-weight:800; color:#DC2626;">{format_vnd(total_rec_amt)}</div></div>')

    st.write("")
    with st.expander("📸 Tải ảnh hóa đơn mới vào kho", expanded=(len(receipts) == 0)):
        up_img = st.file_uploader("Chọn ảnh hóa đơn (JPG, PNG):", type=["jpg", "jpeg", "png"], key="gal_up")
        g1, g2, g3 = st.columns(3)
        with g1:
            g_cat = st.selectbox("Danh mục:", list(EXPENSE_CATEGORIES.keys()), key="g_cat")
        with g2:
            g_amt = st.number_input("Số tiền trên hóa đơn (đ):", min_value=0, max_value=500_000_000, value=65_000, step=5_000, key="g_amt")
        with g3:
            g_note = st.text_input("Tên quán / Ghi chú:", placeholder="VD: Bách Hóa Xanh, Highland...", key="g_note")
        if st.button("💾 Lưu vào Kho ảnh & Ghi sổ chi tiêu", type="primary"):
            if up_img is not None:
                fname = f"receipt_{uuid4().hex}"
                fpath = os.path.join(RECEIPTS_DIR, fname)
                with open(fpath, "wb") as f:
                    f.write(up_img.getbuffer())
                receipts.insert(0, {
                    "id": fname,
                    "file": fname, "date": date.today().strftime("%d/%m/%Y"),
                    "category": g_cat, "amount": float(g_amt),
                    "note": g_note.strip() or up_img.name
                })
                save_receipts_meta(receipts)
                if g_amt > 0:
                    backend.add_daily_transaction(date.today().strftime("%Y-%m-%d"), "Chi tiêu", g_cat, float(g_amt), f"[Hóa đơn] {g_note.strip() or up_img.name}")
                st.toast("Đã lưu ảnh hóa đơn thành công!", icon="🖼️")
                st.rerun()
            else:
                st.warning("Vui lòng chọn 1 file ảnh hóa đơn trước.")

    if receipts:
        g_cols = st.columns(2, gap="medium")
        for idx, rec in enumerate(receipts):
            fpath = os.path.join(RECEIPTS_DIR, rec["file"])
            with g_cols[idx % 2]:
                with st.container(border=True):
                    if os.path.exists(fpath):
                        st.image(fpath, use_container_width=True)
                    st.markdown(f"**{rec['note']}** · `{rec['category']}` · **{format_vnd(rec['amount'])}** ({rec['date']})")
                    if st.button("🗑️ Xóa ảnh này", key=f"del_rec_{rec['id']}", use_container_width=True):
                        if os.path.exists(fpath):
                            os.remove(fpath)
                        receipts = [x for x in receipts if x["id"] != rec["id"]]
                        save_receipts_meta(receipts)
                        st.rerun()
    else:
        st.info("Kho ảnh hóa đơn đang trống. Bạn có thể tải ảnh ở khung trên hoặc dùng mục **Quét hóa đơn AI**.")


# =============================================================================
# TRANG 4: THỐNG KÊ CHI TIÊU (TIỀN ĂN • TIỀN TRỌ • ĐI LẠI & BIỂU ĐỒ)
# =============================================================================
elif st.session_state.nav_page == "Thống kê chi tiêu":
    render_kpi_row()
    for a in alerts:
        if a["level"] == "danger":
            st.html(f'<div class="alert-row-red"><span>⚠️ {a["message"]}</span><span style="font-size:11.5px; background:rgba(239,68,68,0.15); padding:3px 10px; border-radius:99px;">Vượt ngân sách</span></div>')

    st.html('<div style="font-size:18px; font-weight:800; margin:12px 0 10px 0;">🍜 Theo dõi 3 khoản chi thiết yếu: Tiền ăn • Tiền trọ • Đi lại</div>')
    e_cols = st.columns(3, gap="medium")
    for idx, item in enumerate(essential_stats):
        pct_b = min(item["percent"], 100.0)
        b_col = "#DC2626" if item["status"] == "danger" else ("#D97706" if item["status"] == "warning" else "#6328E8")
        with e_cols[idx]:
            st.html(f"""
            <div class="kpi-3d-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:16px; font-weight:700;">{item['icon']} {item['category']}</span>
                    <span style="font-size:12px; font-weight:700; color:{b_col};">{item['percent']:.1f}%</span>
                </div>
                <div style="font-size:24px; font-weight:800; color:{b_col};">{format_vnd(item['spent'])}</div>
                <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">Định mức: {format_vnd(item['limit'])} · Tỷ trọng {item['share_of_total']:.1f}%</div>
                <div class="progress-track"><div class="progress-fill-shimmer" style="width:{pct_b:.1f}%; background:{b_col};"></div></div>
                <div style="font-size:12.5px; font-weight:600;">{item['note_text']}</div>
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
                    color=alt.Color("category:N", title="Danh mục", scale=alt.Scale(scheme="purples")),
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
                    color=alt.Color("tx_type:N", title="Loại", scale=alt.Scale(domain=["Thu nhập", "Chi tiêu"], range=["#6328E8", "#EC4899"])),
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
                    color=alt.Color("category:N", title="Nhóm chính", scale=alt.Scale(domain=["Tiền ăn", "Tiền trọ", "Đi lại"], range=["#EC4899", "#6328E8", "#0EA5E9"])),
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
                    line={"color": "#6328E8", "strokeWidth": 2.5},
                    color=alt.Gradient(gradient="linear", stops=[alt.GradientStop(color="rgba(99,40,232,0.38)", offset=0), alt.GradientStop(color="rgba(99,40,232,0.02)", offset=1)], x1=1, x2=1, y1=1, y2=0),
                    point=alt.OverlayMarkDef(color="#6328E8", size=60)
                )
                .encode(
                    x=alt.X("date:N", title="Ngày", axis=alt.Axis(labelAngle=-30)),
                    y=alt.Y("amount:Q", title="VNĐ"),
                    tooltip=[alt.Tooltip("date:N"), alt.Tooltip("amount:Q", format=",.0f")]
                )
                .properties(height=270, title=f"Chi tiêu hằng ngày tháng {selected_month}")
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
# TRANG 5: AI LÀM SẠCH DỮ LIỆU THÔ
# =============================================================================
elif st.session_state.nav_page == "AI Làm sạch dữ liệu":
    mode_clean = st.radio("Nguồn dữ liệu thô:", ["Dán văn bản / ghi chú thô", "Tải file CSV thô"], horizontal=True)

    if mode_clean == "Dán văn bản / ghi chú thô":
        raw_txt = st.text_area(
            "Dán ghi chú chi tiêu lộn xộn của bạn vào đây (mỗi khoản 1 dòng hoặc cách nhau dấu phẩy):",
            value="Sáng ăn phở bò 40k\nĐổ xăng xe máy 65k, gửi xe trường 5k\nĐóng tiền trọ tháng 11 1tr85\nNhận lương gia sư 1.5 triệu",
            height=150
        )
        if st.button("🤖 AI Phân tích & Làm sạch dữ liệu", type="primary"):
            parsed = parse_raw_notes_to_rows(raw_txt)
            st.session_state.cleaned_preview = parsed

        if st.session_state.get("cleaned_preview"):
            df_prev = pd.DataFrame(st.session_state.cleaned_preview)
            st.success(f"Đã bóc tách sạch **{len(df_prev)}** giao dịch chuẩn:")
            st.dataframe(df_prev, use_container_width=True, hide_index=True)
            if st.button("💾 Lưu toàn bộ dữ liệu đã làm sạch vào SQLite", type="primary"):
                cnt = 0
                for row in st.session_state.cleaned_preview:
                    ok, _ = backend.add_daily_transaction(row["date"], row["tx_type"], row["category"], float(row["amount"]), row["note"])
                    if ok:
                        cnt += 1
                st.session_state.cleaned_preview = []
                st.toast(f"Đã lưu {cnt} giao dịch sạch vào sổ!", icon="✨")
                st.rerun()
    else:
        up_raw = st.file_uploader("Chọn file CSV thô để làm sạch & nhập sổ:", type=["csv"])
        if up_raw is not None:
            try:
                df_raw = pd.read_csv(up_raw)
                st.dataframe(df_raw.head(20), use_container_width=True)
                col_map = {
                    "Ngày giao dịch": "date", "Ngày": "date",
                    "Loại giao dịch": "tx_type", "Loại": "tx_type",
                    "Danh mục": "category",
                    "Số tiền (VNĐ)": "amount", "Số tiền": "amount",
                    "Ghi chú chi tiết": "note", "Ghi chú": "note",
                }
                df_c = df_raw.rename(columns={k: v for k, v in col_map.items() if k in df_raw.columns})
                if {"date", "tx_type", "category", "amount"}.issubset(set(df_c.columns)):
                    df_valid = df_c[df_c["tx_type"].isin(["Chi tiêu", "Thu nhập"])]
                    if st.button(f"💾 Nhập {len(df_valid)} dòng hợp lệ vào sổ", type="primary"):
                        ok_c = 0
                        for _, r in df_valid.iterrows():
                            rd = str(r["date"]).strip()
                            try:
                                p_dt = pd.to_datetime(rd, dayfirst="/" in rd).strftime("%Y-%m-%d")
                            except Exception:
                                continue
                            av = float(str(r["amount"]).replace(".", "").replace(",", "").replace("đ", "").strip())
                            nv = "" if pd.isna(r.get("note")) else str(r.get("note"))
                            ok, _ = backend.add_daily_transaction(p_dt, str(r["tx_type"]).strip(), str(r["category"]).strip(), av, nv)
                            if ok:
                                ok_c += 1
                        st.toast(f"Đã làm sạch & lưu {ok_c} giao dịch!", icon="✨")
                        st.rerun()
                else:
                    st.warning("File CSV cần có các cột: `Ngày giao dịch`, `Loại giao dịch`, `Danh mục`, `Số tiền (VNĐ)`.")
            except Exception as e:
                st.error(f"Không đọc được file: {e}")


# =============================================================================
# TRANG 6: QUÉT HÓA ĐƠN AI (TẢI ẢNH / CAMERA / DÁN VĂN BẢN HÓA ĐƠN)
# =============================================================================
elif st.session_state.nav_page == "Quét hóa đơn AI":
    ocr_mode = st.radio("Chọn cách nhập hóa đơn:", ["📁 Tải ảnh hóa đơn (JPG/PNG)", "📸 Chụp bằng Camera", "📝 Dán nội dung hóa đơn (OCR text)"], horizontal=True)

    ocr_img_file = None
    ocr_text_in = ""
    if ocr_mode == "📁 Tải ảnh hóa đơn (JPG/PNG)":
        ocr_img_file = st.file_uploader("Tải ảnh biên lai / hóa đơn:", type=["jpg", "jpeg", "png"], key="ocr_upload")
        if ocr_img_file:
            st.image(ocr_img_file, width=320, caption="Ảnh hóa đơn vừa tải lên")
        ocr_text_in = st.text_input("Ghi chú / Nội dung hóa đơn (nếu muốn tự động bóc số tiền):", placeholder="VD: Bách Hóa Xanh - Tổng cộng 145.000đ")
    elif ocr_mode == "📸 Chụp bằng Camera":
        ocr_img_file = st.camera_input("Đưa hóa đơn trước camera để chụp")
        ocr_text_in = st.text_input("Ghi chú ngắn cho hóa đơn vừa chụp:", placeholder="VD: Cơm tấm 45k")
    else:
        ocr_text_in = st.text_area(
            "Dán nội dung chữ từ hóa đơn điện tử / Momo / Banking:",
            value="SIÊU THỊ CO.OPMART\nThịt heo + Rau xanh + Trứng\nTổng thanh toán: 185.000 đ",
            height=130
        )

    detected_amt = parse_vietnamese_amount(ocr_text_in) if ocr_text_in.strip() else 0.0
    det_type, det_cat = classify_vietnamese_tx(ocr_text_in) if ocr_text_in.strip() else ("Chi tiêu", "Tiền ăn")

    st.markdown("#### 🔍 Kết quả nhận diện & xác nhận lưu")
    with st.form("ocr_confirm_form"):
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            f_cat = st.selectbox("Danh mục nhận diện:", list(EXPENSE_CATEGORIES.keys()), index=list(EXPENSE_CATEGORIES.keys()).index(det_cat) if det_cat in EXPENSE_CATEGORIES else 0)
        with oc2:
            f_amt = st.number_input("Số tiền (VNĐ):", min_value=0, max_value=500_000_000, value=int(detected_amt) if detected_amt > 0 else 50_000, step=5_000)
        with oc3:
            f_date = st.date_input("Ngày hóa đơn:", value=date.today())
        f_note = st.text_input("Ghi chú lưu vào sổ:", value=ocr_text_in.strip().splitlines()[0] if ocr_text_in.strip() else "Hóa đơn quét AI")
        save_to_gallery = st.checkbox("Lưu luôn ảnh vào Kho ảnh hóa đơn", value=True)

        if st.form_submit_button("🔍 Xác nhận & Lưu giao dịch hóa đơn", type="primary", use_container_width=True):
            ok, msg = backend.add_daily_transaction(f_date.strftime("%Y-%m-%d"), "Chi tiêu", f_cat, float(f_amt), f"[Quét HĐ] {f_note}")
            if ok:
                if save_to_gallery and ocr_img_file is not None:
                    fname = f"ocr_{uuid4().hex}"
                    with open(os.path.join(RECEIPTS_DIR, fname), "wb") as f_out:
                        f_out.write(ocr_img_file.getbuffer())
                    recs = load_receipts_meta()
                    recs.insert(0, {"id": fname, "file": fname, "date": f_date.strftime("%d/%m/%Y"), "category": f_cat, "amount": float(f_amt), "note": f_note})
                    save_receipts_meta(recs)
                st.toast("✅ Đã lưu hóa đơn vào sổ chi tiêu!", icon="📷")
                st.success("✅ Đã lưu hóa đơn thành công!")
                st.rerun()
            else:
                st.error(msg)


# =============================================================================
# TRANG 7: NHẬP GIỌNG NÓI (GHI ÂM MICRO + PHÂN TÍCH CÂU NÓI TIẾNG VIỆT)
# =============================================================================
elif st.session_state.nav_page == "Nhập giọng nói":
    v_col1, v_col2 = st.columns([1.05, 1.25], gap="large")
    with v_col1:
        st.html("""
        <div class="glass-panel" style="text-align:center;">
            <div class="mic-pulse-ring">🎙️</div>
            <div style="font-size:18px; font-weight:800; margin-bottom:4px;">Ghi âm khoản chi tiêu</div>
            <div style="font-size:13px; color:var(--text-muted); margin-bottom:10px;">
                Bấm nút Micro bên dưới để thu âm trực tiếp hoặc chọn câu mẫu để kiểm thử phân tích AI
            </div>
        </div>
        """)
        audio_clip = st.audio_input("Nhấn biểu tượng micro để bắt đầu ghi âm giọng nói:")
        if audio_clip is not None:
            st.success("🎙️ Đã thu âm thành công! Nhập hoặc xác nhận nội dung câu nói bên phải để lưu vào sổ.")

        st.markdown("**💡 Câu mẫu thử nhanh (bấm để điền):**")
        s1, s2 = st.columns(2)
        with s1:
            if st.button("🍜 \"Trưa ăn cơm sườn 45k\"", use_container_width=True):
                st.session_state.voice_text_val = "Trưa nay ăn cơm sườn ở căn tin 45k"
                st.rerun()
        with s2:
            if st.button("🛵 \"Đổ xăng xe máy 65k\"", use_container_width=True):
                st.session_state.voice_text_val = "Đổ xăng xe máy 65k và gửi xe 5k"
                st.rerun()

    with v_col2:
        st.markdown("#### 🧠 Phân tích câu nói tiếng Việt")
        voice_sentence = st.text_input(
            "Lời bạn nói:",
            value=st.session_state.voice_text_val,
            placeholder="VD: Sáng ăn bánh mì 20k, đổ xăng 50k, nhận tiền bố mẹ gửi 4tr5..."
        )
        st.session_state.voice_text_val = voice_sentence

        if voice_sentence.strip():
            parsed_voice = parse_raw_notes_to_rows(voice_sentence)
            if parsed_voice:
                st.success(f"Đã phân tích được **{len(parsed_voice)}** khoản từ câu nói của bạn:")
                st.dataframe(pd.DataFrame(parsed_voice), use_container_width=True, hide_index=True)
                if st.button("🧠 Lưu ngay vào sổ chi tiêu", type="primary", use_container_width=True):
                    ok_v = 0
                    for row in parsed_voice:
                        ok, _ = backend.add_daily_transaction(row["date"], row["tx_type"], row["category"], float(row["amount"]), f"[Giọng nói] {row['note']}")
                        if ok:
                            ok_v += 1
                    st.session_state.voice_text_val = ""
                    st.toast(f"✅ Đã lưu {ok_v} giao dịch từ giọng nói!", icon="🎙️")
                    st.rerun()
            else:
                st.warning("Chưa nhận ra số tiền trong câu nói. Thử ghi kèm số tiền như `45k`, `1tr5`, `50.000đ`.")


# =============================================================================
# TRANG 8: CÁ NHÂN, NGÂN SÁCH & SỔ GIAO DỊCH XUẤT / NHẬP CSV
# =============================================================================
elif st.session_state.nav_page == "Cá nhân & Tài khoản":
    tab_so, tab_ngansach = st.tabs(["📝 Sổ giao dịch & Xuất/Nhập CSV", "⚙️ Cài đặt Định mức Ngân sách"])

    with tab_so:
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

        f1, f2, f3, f4, f5 = st.columns([0.95, 0.95, 1.2, 0.95, 0.95])
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
            st.write("")
            if not df_show.empty:
                df_exp = df_show.sort_values(by=["date", "id"]).reset_index(drop=True)
                df_exp.insert(0, "STT", range(1, len(df_exp) + 1))
                df_exp["Ngày giao dịch"] = pd.to_datetime(df_exp["date"]).dt.strftime("%d/%m/%Y")
                df_exp["Số tiền (VNĐ)"] = df_exp["amount"].astype(int)
                df_csv = df_exp[["STT", "id", "Ngày giao dịch", "tx_type", "category", "Số tiền (VNĐ)", "note"]].rename(
                    columns={"id": "Mã GD", "tx_type": "Loại giao dịch", "category": "Danh mục", "note": "Ghi chú chi tiết"}
                )
                exp_thu = int(df_show[df_show["tx_type"] == "Thu nhập"]["amount"].sum())
                exp_chi = int(df_show[df_show["tx_type"] == "Chi tiêu"]["amount"].sum())
                sum_df = pd.DataFrame([
                    {"STT": "", "Mã GD": "", "Ngày giao dịch": "", "Loại giao dịch": "TỔNG THU", "Danh mục": "", "Số tiền (VNĐ)": exp_thu, "Ghi chú chi tiết": "Tổng cộng thu nhập"},
                    {"STT": "", "Mã GD": "", "Ngày giao dịch": "", "Loại giao dịch": "TỔNG CHI", "Danh mục": "", "Số tiền (VNĐ)": exp_chi, "Ghi chú chi tiết": "Tổng cộng chi tiêu"},
                    {"STT": "", "Mã GD": "", "Ngày giao dịch": "", "Loại giao dịch": "CHÊNH LỆCH", "Danh mục": "", "Số tiền (VNĐ)": exp_thu - exp_chi, "Ghi chú chi tiết": "Tổng Thu - Tổng Chi"},
                ])
                csv_bytes = pd.concat([df_csv, sum_df], ignore_index=True).to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 Xuất CSV", data=csv_bytes, file_name=f"UTH_chi_tieu_{selected_month}.csv", mime="text/csv", use_container_width=True)
        with f5:
            st.write("")
            if st.button("🔄 Dữ liệu mẫu", use_container_width=True):
                backend.reset_demo_data()
                st.toast("Đã khôi phục dữ liệu mẫu 4 tháng!", icon="💜")
                st.rerun()

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
            dc1, dc2 = st.columns([3, 1])
            with dc1:
                tx_map = {row["id"]: f"#{row['id']} | {row['date']} | {row['category']} | {format_vnd(row['amount'])}" for _, row in df_show.iterrows()}
                del_id = st.selectbox("Chọn giao dịch cần xóa:", list(tx_map.keys()), format_func=lambda x: tx_map[x])
            with dc2:
                st.write("")
                if st.button("🗑️ Xóa giao dịch", use_container_width=True):
                    if backend.remove_transaction(int(del_id)):
                        st.toast(f"Đã xóa #{del_id}", icon="🗑️")
                        st.rerun()

    with tab_ngansach:
        with st.form(f"uth_budget_form_{selected_month}"):
            new_tot = st.number_input("🎯 Tổng ngân sách tháng (VNĐ):", min_value=500_000, max_value=100_000_000, value=int(budget_cfg.total_budget), step=100_000, key=f"budget_total_{selected_month}")
            new_lims = {}
            bc1, bc2 = st.columns(2)
            cats_list = list(EXPENSE_CATEGORIES.items())
            for i, (cat, meta) in enumerate(cats_list):
                with (bc1 if i % 2 == 0 else bc2):
                    new_lims[cat] = float(
                        st.number_input(
                            f"{meta['icon']} Định mức {cat}:",
                            min_value=0, max_value=50_000_000,
                            value=int(budget_cfg.category_limits.get(cat, 300_000)),
                            step=50_000, key=f"uth_lim_{selected_month}_{cat}"
                        )
                    )
            if st.form_submit_button("💾 Lưu cấu hình ngân sách", type="primary", use_container_width=True):
                backend.update_budget(selected_month, float(new_tot), new_lims)
                st.toast("Đã lưu định mức mới!", icon="💜")
                st.rerun()
