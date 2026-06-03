"""
SSH Tool 主入口 — 支持 CLI / GUI 双模式
=========================================

修改日期: 2026-06-03
迭代: v2.0
修改内容: 重构 main() 函数, 新增 _run_cli() / _run_gui() 双模式
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


def _run_gui(args: argparse.Namespace) -> int:
    """使用 Solo Leveling 风格 GUI 执行 SSH 操作。"""
    from ssh_tool.sl_gui import GuiOutput, SoloLevelingGUI

    msg_queue: queue.Queue = queue.Queue()
    gui = SoloLevelingGUI(msg_queue)
    gui_output = GuiOutput(msg_queue)

    exit_code = [1]  # 用于跨线程传递结果

    def worker() -> None:
        log_path = create_log_file(Path.cwd())
        try:
            gui_output.header("SSH Tool")
            append_log(log_path, "SSH Tool started.")
            ssh_config_path = Path(args.ssh_config)
            operations_path = Path(args.operations)
            ssh_config = load_ssh_config(ssh_config_path)
            operations = load_operations(operations_path)

            # 告知 GUI 总步骤数
            gui_output.set_total_steps(len(operations))

            gui_output.connection(ssh_config.username, ssh_config.host, ssh_config.port, ssh_config.target_os)
            append_log(log_path, f"Connecting to {ssh_config.username}@{ssh_config.host}:{ssh_config.port} ({ssh_config.target_os})")
            with SshRemote(ssh_config, output=gui_output.remote) as remote:
                runner = OperationRunner(remote, target_os=ssh_config.target_os, output=gui_output.line)
                # 包装 runner.run_all 以更新进度
                for i, op in enumerate(operations, start=1):
                    from ssh_tool.config import CommandOperation, UploadOperation
                    if isinstance(op, UploadOperation):
                        gui_output.line(f"upload {op.local_path} -> {op.remote_path}")
                        remote.upload(op.local_path, op.remote_path)
                    else:
                        runner._run_command(op)
                    gui_output.update_progress(i, len(operations))

            gui_output.success("All operations completed.")
            append_log(log_path, "All operations completed.")
            exit_code[0] = 0
        except Exception as exc:
            write_failure_log(log_path, exc)
            gui_output.error(str(exc), str(log_path))
            exit_code[0] = 1
        finally:
            # 发送结束信号，让 GUI 知道工作线程已结束
            msg_queue.put(("_done",))

    # 检测 done 信号，延迟关闭窗口
    def _check_done() -> None:
        try:
            while True:
                msg = msg_queue.get_nowait()
                if msg[0] == "_done":
                    gui.root.after(3000, gui.root.destroy)
                    return
        except queue.Empty:
            pass
        finally:
            gui.root.after(100, _check_done)

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    # 启动后台检测 done
    gui.root.after(100, _check_done)

    gui.run()
    return exit_code[0]


if __name__ == "__main__":
    raise SystemExit(main())
