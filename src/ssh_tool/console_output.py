from __future__ import annotations

from collections.abc import Callable


class ConsoleOutput:
    def __init__(self, write: Callable[[str], None] = print, width: int = 72) -> None:
        self.write = write
        self.width = max(width, 32)

    def header(self, title: str) -> None:
        inner_width = self.width - 2
        border = "+" + "-" * inner_width + "+"
        self.write(border)
        self.write("| " + title[: inner_width - 2].ljust(inner_width - 2) + " |")
        self.write(border)

    def connection(self, username: str, host: str, port: int, target_os: str) -> None:
        self.info(f"Connecting to {username}@{host}:{port} ({target_os})")

    def info(self, message: str) -> None:
        self.write(f"[INFO] {message}")

    def line(self, message: str) -> None:
        if message.startswith("[line "):
            self.write(f"[STEP] {message}")
        else:
            self.write(message)

    def remote(self, text: str) -> None:
        for raw_line in text.splitlines():
            self.write(f"       {raw_line}")

    def success(self, message: str) -> None:
        self.write(f"[ OK ] {message}")

    def error(self, message: str, log_path: str) -> None:
        self.write(f"[FAIL] {message}")
        self.write(f"[LOG ] {log_path}")
