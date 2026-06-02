from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


TargetOs = Literal["linux", "windows"]


@dataclass(frozen=True)
class SshConfig:
    host: str
    port: int
    username: str
    password: str
    target_os: TargetOs = "linux"
    output_encoding: str = "auto"
    timeout: int = 30


@dataclass(frozen=True)
class CommandOperation:
    command: str
    line_number: int


@dataclass(frozen=True)
class UploadOperation:
    local_path: Path
    remote_path: str
    line_number: int


Operation = CommandOperation | UploadOperation


def load_ssh_config(path: Path) -> SshConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    required_fields = ["host", "port", "username", "password"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValueError(f"{path} is missing required field(s): {', '.join(missing)}")

    target_os = str(data.get("target_os", "linux")).lower()
    if target_os not in ("linux", "windows"):
        raise ValueError(f'{path} field "target_os" must be "linux" or "windows"')

    return SshConfig(
        host=str(data["host"]),
        port=int(data["port"]),
        username=str(data["username"]),
        password=str(data["password"]),
        target_os=target_os,  # type: ignore[arg-type]
        output_encoding=str(data.get("output_encoding", "auto")).lower(),
        timeout=int(data.get("timeout", 30)),
    )


def load_operations(path: Path) -> list[Operation]:
    operations: list[Operation] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("upload "):
            operations.append(_parse_upload(line, line_number))
        else:
            operations.append(CommandOperation(command=line, line_number=line_number))

    return operations


def _parse_upload(line: str, line_number: int) -> UploadOperation:
    try:
        parts = shlex.split(line, posix=False)
    except ValueError as exc:
        raise ValueError(f"Invalid upload syntax at line {line_number}: {exc}") from exc

    if len(parts) != 3 or parts[0] != "upload":
        raise ValueError(
            f"Invalid upload syntax at line {line_number}. "
            "Use: upload <local_file> <remote_file>"
        )

    local_path = parts[1].strip('"')
    remote_path = parts[2].strip('"')
    return UploadOperation(local_path=Path(local_path), remote_path=remote_path, line_number=line_number)
