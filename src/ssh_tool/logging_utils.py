from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path


def create_log_file(base_dir: Path, timestamp: str | None = None) -> Path:
    stamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"run-{stamp}.log"


def append_log(log_path: Path, message: str) -> None:
    with log_path.open("a", encoding="utf-8") as file:
        file.write(message.rstrip() + "\n")


def write_failure_log(log_path: Path, exc: Exception) -> None:
    append_log(log_path, f"ERROR: {exc}")
    append_log(log_path, traceback.format_exc())
