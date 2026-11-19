"""Trang Streamlit; có thể chạy trực tiếp hoặc thông qua main.py."""

import argparse
import runpy
import sys
from pathlib import Path

from expense_tracker.ui import run_app


def main():
    if len(sys.argv) == 1:
        runpy.run_module("unispend_3d.app", run_name="__main__")
        return

    parser = argparse.ArgumentParser(description="UniSpend — Quản lý chi tiêu sinh viên")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--db", type=Path)
    args = parser.parse_args()
    if args.demo and args.db:
        parser.error("Không dùng --demo cùng --db để tránh trộn dữ liệu mẫu.")
    base = Path(__file__).resolve().parent
    db_path = args.db or base / "data" / ("demo.db" if args.demo else "expenses.db")
    run_app(db_path, demo=args.demo)


if __name__ == "__main__":
    main()
