"""Mở giao diện UniSpend trên trình duyệt bằng Streamlit."""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


def main():
    args = sys.argv[1:]
    if not args or "--api" in args:
        from unispend_3d.main import main as run_uth

        return run_uth()

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="UniSpend UTH (mặc định). Dùng --api để chạy FastAPI.")
    parser.add_argument("--legacy", action="store_true", help="Mở giao diện cũ với dữ liệu ở thư mục data")
    parser.add_argument("--demo", action="store_true", help="Mở dữ liệu mẫu tách riêng")
    parser.add_argument("--db", type=Path, help="Đường dẫn tới tệp SQLite khác")
    args = parser.parse_args()
    if args.demo and args.db:
        parser.error("Không dùng --demo cùng --db để tránh trộn dữ liệu mẫu.")
    base = Path(__file__).resolve().parent
    db_path = args.db or base / "data" / ("demo.db" if args.demo else "expenses.db")
    interpreter = sys.executable
    if importlib.util.find_spec("streamlit") is None:
        local_python = base / ".venv" / "Scripts" / "python.exe"
        if local_python.exists() and local_python.resolve() != Path(sys.executable).resolve():
            interpreter = str(local_python)
        else:
            print("Cài thư viện trước khi chạy: python -m pip install -r requirements.txt", file=sys.stderr)
            return 1
    command = [interpreter, "-m", "streamlit", "run", str(base / "app.py"),
               "--server.address=127.0.0.1", "--browser.gatherUsageStats=false", "--"]
    if args.demo:
        command.append("--demo")
    else:
        command.extend(["--db", str(db_path.resolve())])
    try:
        return subprocess.run(command, cwd=base).returncode
    except OSError as exc:
        print(f"Không khởi động được ứng dụng: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
