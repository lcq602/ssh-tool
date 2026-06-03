from __future__ import annotations

import ntpath
from pathlib import PurePosixPath
from typing import Callable, Protocol

from ssh_tool.config import CommandOperation, Operation, TargetOs, UploadOperation


class Remote(Protocol):
    def run(self, command: str) -> int:
        ...

    def upload(self, local_path, remote_path: str) -> None:  # type: ignore[no-untyped-def]
        ...


class OperationRunner:
    def __init__(self, remote: Remote, target_os: TargetOs = "linux", output: Callable[[str], None] = print) -> None:
        self.remote = remote
        self.target_os = target_os
        self.current_dir: str | None = None
        self.output = output

    def run_all(self, operations: list[Operation]) -> None:
        for operation in operations:
            if isinstance(operation, UploadOperation):
                self.output(f"[line {operation.line_number}] upload {operation.local_path} -> {operation.remote_path}")
                self.remote.upload(operation.local_path, operation.remote_path)
                continue

            self._run_command(operation)

    def _run_command(self, operation: CommandOperation) -> None:
        command = operation.command
        if command == "cd" or command.startswith("cd "):
            self.current_dir = _resolve_cd(self.current_dir, command, self.target_os)
            self.output(f"[line {operation.line_number}] current directory: {self.current_dir}")
            return

        remote_command = command
        if self.current_dir:
            remote_command = _with_current_dir(self.current_dir, command, self.target_os)

        self.output(f"[line {operation.line_number}] $ {remote_command}")
        exit_code = self.remote.run(remote_command)
        if exit_code != 0:
            raise RuntimeError(f"Command failed at line {operation.line_number} with exit code {exit_code}: {command}")


def _resolve_cd(current_dir: str | None, command: str, target_os: TargetOs) -> str:
    target = command[2:].strip() or "~"
    target = target.strip('"')
    if target_os == "windows":
        return _resolve_windows_cd(current_dir, target)

    if target.startswith("/"):
        return target
    if target == "~":
        return "~"
    if current_dir and current_dir != "~":
        return str(PurePosixPath(current_dir) / target)
    return target


def _resolve_windows_cd(current_dir: str | None, target: str) -> str:
    if target in (".", ""):
        return current_dir or "."
    if target.startswith("%") or ntpath.isabs(target):
        return target
    if current_dir:
        return ntpath.normpath(ntpath.join(current_dir, target))
    return target


def _with_current_dir(current_dir: str, command: str, target_os: TargetOs) -> str:
    if target_os == "windows":
        escaped_dir = current_dir.replace('"', '\\"')
        return f'cd /d "{escaped_dir}" && {command}'
    return f"cd {current_dir} && {command}"
