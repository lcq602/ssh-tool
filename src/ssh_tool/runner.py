"""
命令操作执行器 — 解析并执行远程命令 / 文件上传
==================================================

提供 OperationRunner 类, 逐条执行 CommandOperation 和 UploadOperation。
支持 --skip-errors 模式跳过失败操作继续执行。

修改日期: 2026-06-04
迭代: v1.1
修改内容: 修复上传路径解析（支持 exe 相对路径）
"""

from __future__ import annotations

import ntpath
import sys
from pathlib import Path, PurePosixPath
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
                resolved = _resolve_local_path(operation.local_path)
                self.output(f"[line {operation.line_number}] upload {resolved} -> {operation.remote_path}")
                self.remote.upload(resolved, operation.remote_path)
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


def _resolve_local_path(local_path: Path) -> Path:
    """解析上传文件的本地路径。

    如果路径不存在且不是绝对路径, 尝试基于 exe 所在目录或 CWD 重新解析。
    这解决了 Windows 上 ``\\target\\file.jar`` 被误判为盘符根目录的问题。
    """
    if local_path.exists():
        return local_path

    # 计算基准目录：打包 exe 用 exe 所在目录, 否则用 CWD
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()

    # 如果原始路径有 . 或 .., 用原始名
    candidate = base / local_path.name if local_path.parent == Path() else base / local_path
    if candidate.exists():
        return candidate.resolve()

    return local_path  # 让 FileNotFoundError 自然抛出


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