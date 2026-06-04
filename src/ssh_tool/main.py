"""
SSH Tool 主入口 — 支持 CLI / GUI 双模式
=========================================

修改日期: 2026-06-04
迭代: v2.2
修改内容: 新增 --skip-errors 跳过失败继续执行; 失败时不自动关闭 GUI 窗口; 修复上传路径解析
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
from pathlib import Path

from ssh_tool.console_output import ConsoleOutput
from ssh_tool.config import load_operations, load_ssh_config
from ssh_tool.logging_utils import append_log, create_log_file, write_failure_log
from ssh_tool.remote import SshRemote
from ssh_tool.runner import OperationRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run configured SSH operations.")
    parser.add_argument("--ssh-config", default="config/ssh.json", help="SSH connection JSON file.")
    parser.add_argument("--operations", default="config/operations.txt", help="Operations text file.")
    parser.add_argument("--no-pause", action="store_true", help="Do not wait for Enter before exit.")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode (no GUI).")
    parser.add_argument("--skip-errors", action="store_true", help="Skip failed operations and continue.")
    args = parser.parse_args(argv)

    # ── 判断是否使用 GUI ──
    use_gui = (
        not args.cli
        and getattr(sys, "frozen", False)
    )

    if use_gui:
        return _run_gui(args)
    else:
        return _run_cli(args)


def _run_cli(args: argparse.Namespace) -> int:
    """原有的控制台执行逻辑。"""
    log_path = create_log_file(Path.cwd())
    console = ConsoleOutput()
    skip_errors = args.skip_errors

    try:
        console.header("SSH Tool")
        append_log(log_path, "SSH Tool started.")
        ssh_config_path = Path(args.ssh_config)
        operations_path = Path(args.operations)
        ssh_config = load_ssh_config(ssh_config_path)
        operations = load_operations(operations_path)

        console.connection(ssh_config.username, ssh_config.host, ssh_config.port, ssh_config.target_os)
        append_log(log_path, f"Connecting to {ssh_config.username}@{ssh_config.host}:{ssh_config.port} ({ssh_config.target_os})")
        with SshRemote(ssh_config, output=console.remote) as remote:
            runner = OperationRunner(remote, target_os=ssh_config.target_os, output=console.line)
            if skip_errors:
                _run_operations_skip_errors(runner, operations)
            else:
                runner.run_all(operations)
        console.success("All operations completed.")
        append_log(log_path, "All operations completed.")
        return 0
    except Exception as exc:
        write_failure_log(log_path, exc)
        console.error(str(exc), str(log_path))
        return 1
    finally:
        if not args.no_pause:
            input("Press Enter to exit...")


def _run_operations_skip_errors(runner: OperationRunner, operations: list[Operation]) -> None:
    """跳过错误模式：逐条执行, 失败时记录原因并继续。"""
    from ssh_tool.config import CommandOperation, UploadOperation

    for op in operations:
        try:
            if isinstance(op, UploadOperation):
                from pathlib import Path
                resolved = _resolve_local_path(op.local_path)
                runner.output(f"[line {op.line_number}] upload {resolved} -> {op.remote_path}")
                runner.remote.upload(resolved, op.remote_path)
            else:
                runner._run_command(op)
        except Exception as exc:
            runner.output(f"[line {op.line_number}] ⚠ SKIPPED: {exc}")


def _resolve_local_path(local_path: Path) -> Path:
    """解析上传文件的本地路径 (适用于 --skip-errors 模式)。"""
    import sys
    from pathlib import Path as _Path

    if local_path.exists():
        return local_path
    base = _Path(sys.executable).parent if getattr(sys, "frozen", False) else _Path.cwd()
    candidate = base / local_path.name if local_path.parent == _Path() else base / local_path
    if candidate.exists():
        return candidate.resolve()
    return local_path


def _run_gui(args: argparse.Namespace) -> int:
    """使用 Solo Leveling 风格 GUI 执行 SSH 操作。"""
    from ssh_tool.config import CommandOperation, UploadOperation
    from ssh_tool.l10n import get_l10n
    from ssh_tool.sl_gui import GuiOutput, SoloLevelingGUI

    l10n = get_l10n()
    msg_queue: queue.Queue = queue.Queue()
    gui = SoloLevelingGUI(msg_queue, l10n=l10n)
    gui_output = GuiOutput(msg_queue)

    exit_code = [1]
    skip_errors = args.skip_errors

    def worker() -> None:
        log_path = create_log_file(Path.cwd())
        has_error = False
        try:
            gui_output.header(l10n.title)
            append_log(log_path, "SSH Tool started.")
            ssh_config_path = Path(args.ssh_config)
            operations_path = Path(args.operations)
            ssh_config = load_ssh_config(ssh_config_path)
            operations = load_operations(operations_path)

            # 发送 step_item 给所有操作
            gui_output.set_total_steps(len(operations))
            for i, op in enumerate(operations):
                text = str(op.command) if isinstance(op, CommandOperation) else f"upload {op.local_path.name}"
                gui_output.step_item(i, text, "pending")

            if operations:
                first_text = (
                    str(operations[0].command)
                    if isinstance(operations[0], CommandOperation)
                    else f"upload {operations[0].local_path.name}"
                )
                gui_output.step_item(0, first_text, "running")

            gui_output.connection(ssh_config.username, ssh_config.host, ssh_config.port, ssh_config.target_os)
            append_log(log_path, f"Connecting to {ssh_config.username}@{ssh_config.host}:{ssh_config.port} ({ssh_config.target_os})")
            with SshRemote(ssh_config, output=gui_output.remote) as remote:
                runner = OperationRunner(remote, target_os=ssh_config.target_os, output=gui_output.line)
                for i, op in enumerate(operations, start=1):
                    try:
                        if isinstance(op, UploadOperation):
                            resolved = _resolve_local_path(op.local_path)
                            gui_output.line(f"upload {resolved} -> {op.remote_path}")
                            remote.upload(resolved, op.remote_path)
                        else:
                            runner._run_command(op)
                    except Exception as exc:
                        gui_output.error(f"[SKIP] {exc}", str(log_path))
                        gui_output.step_item(i - 1, "", "error")
                        has_error = True
                        if not skip_errors:
                            raise
                    else:
                        gui_output.update_progress(i, len(operations))
                        if i < len(operations):
                            next_op = operations[i]
                            next_text = (
                                str(next_op.command)
                                if isinstance(next_op, CommandOperation)
                                else f"upload {next_op.local_path.name}"
                            )
                            gui_output.step_item(i, next_text, "running")

            if has_error:
                gui_output.info(l10n.log_info.format(msg="Some operations were skipped due to errors"))
                append_log(log_path, "Completed with errors (skip-errors mode).")
                exit_code[0] = 1
            else:
                gui_output.success(l10n.all_done)
                append_log(log_path, "All operations completed.")
                exit_code[0] = 0
        except Exception as exc:
            write_failure_log(log_path, exc)
            gui_output.error(str(exc), str(log_path))
            exit_code[0] = 1
        finally:
            # 发送结束信号
            msg_queue.put(("_done",))

    # 检测 done 信号：成功则 3s 后关, 失败则保留窗口
    def _check_done() -> None:
        try:
            while True:
                msg = msg_queue.get_nowait()
                if msg[0] == "_done":
                    if exit_code[0] == 0:
                        gui.root.after(3000, gui.root.destroy)
                    # 失败时不关窗口, 用户手动点 ✕ 关闭
                    return
        except queue.Empty:
            pass
        finally:
            gui.root.after(100, _check_done)

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    gui.root.after(100, _check_done)

    gui.run()
    return exit_code[0]


if __name__ == "__main__":
    raise SystemExit(main())
