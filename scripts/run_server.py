"""Start the isolated preview from the repository root."""

import subprocess
from pathlib import Path
import sys

if __name__ == "__main__":
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "demo.server:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=Path(__file__).resolve().parents[1],
        )
    )
