"""Khởi chạy giao diện UniSpend 3D với dữ liệu riêng trong thư mục này."""

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Khởi chạy UniSpend")
    parser.add_argument("--api", action="store_true", help="Chạy FastAPI tại cổng 8000")
    parser.add_argument("--db", type=Path, help="Chọn tệp SQLite")
    args = parser.parse_args()
    base_dir = Path(__file__).resolve().parent
    module = "fastapi" if args.api else "streamlit"
    interpreter = sys.executable
    if importlib.util.find_spec(module) is None:
        scripts = "Scripts/python.exe" if os.name == "nt" else "bin/python"
        local_python = next((folder / ".venv" / scripts for folder in (base_dir, base_dir.parent)
                             if (folder / ".venv" / scripts).is_file()), None)
        if local_python and local_python.resolve() != Path(sys.executable).resolve():
            interpreter = str(local_python)
        else:
            print(
                f"Chưa có {module}. Cài thư viện từ {base_dir / 'requirements.txt'}.",
                file=sys.stderr,
            )
            return 1

    env = os.environ.copy()
    db = args.db or env.get("UNISPEND_DB")
    if db:
        env["UNISPEND_DB"] = str(Path(db).expanduser().resolve())

    if args.api:
        command = [interpreter, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", "8000"]
    else:
        command = [interpreter, "-m", "streamlit", "run", str(base_dir / "app.py"),
                   "--server.address=127.0.0.1", "--browser.gatherUsageStats=false"]
    try:
        return subprocess.run(command, cwd=base_dir, env=env).returncode
    except OSError as exc:
        print(f"Không khởi động được UniSpend 3D: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
