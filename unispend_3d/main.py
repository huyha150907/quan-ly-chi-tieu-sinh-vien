"""Khởi chạy giao diện UniSpend 3D với dữ liệu riêng trong thư mục này."""

import importlib.util
import subprocess
import sys
from pathlib import Path


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    base_dir = Path(__file__).resolve().parent
    interpreter = sys.executable
    if importlib.util.find_spec("streamlit") is None:
        local_python = base_dir.parent / ".venv" / "Scripts" / "python.exe"
        if local_python.is_file() and local_python.resolve() != Path(sys.executable).resolve():
            interpreter = str(local_python)
        else:
            print(
                "Chưa có Streamlit. Tại thư mục gốc dự án, chạy: "
                "python -m pip install -r requirements.txt",
                file=sys.stderr,
            )
            return 1

    command = [
        interpreter, "-m", "streamlit", "run", str(base_dir / "app.py"),
        "--server.address=127.0.0.1", "--browser.gatherUsageStats=false",
    ]
    try:
        return subprocess.run(command, cwd=base_dir).returncode
    except OSError as exc:
        print(f"Không khởi động được UniSpend 3D: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
