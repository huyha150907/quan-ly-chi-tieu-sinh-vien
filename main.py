"""Điểm chạy ứng dụng quản lý chi tiêu sinh viên."""

import argparse
import sqlite3
import sys
from pathlib import Path

from expense_tracker.storage import ExpenseStore


def main():
    parser = argparse.ArgumentParser(description="Ứng dụng quản lý chi tiêu sinh viên")
    parser.add_argument("--demo", action="store_true", help="Mở dữ liệu mẫu tách riêng")
    parser.add_argument("--db", type=Path, help="Đường dẫn tới tệp SQLite khác")
    args = parser.parse_args()
    if args.demo and args.db:
        parser.error("Không dùng --demo cùng --db để tránh trộn dữ liệu mẫu.")
    base = Path(__file__).resolve().parent
    db_path = args.db or base / "data" / ("demo.db" if args.demo else "expenses.db")
    store = None
    try:
        from expense_tracker.ui import ExpenseApp

        store = ExpenseStore(db_path)
        if args.demo:
            store.seed_demo()
        app = ExpenseApp(store, demo=args.demo)
        app.mainloop()
    except (OSError, sqlite3.Error) as exc:
        print(f"Không mở được dữ liệu: {exc}", file=sys.stderr)
        return 1
    finally:
        if store is not None:
            store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
