from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ssh_tool.config import load_operations, load_ssh_config
from ssh_tool.logging_utils import append_log, create_log_file, write_failure_log
from ssh_tool.remote import SshRemote
from ssh_tool.runner import OperationRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run configured SSH operations.")
    parser.add_argument("--ssh-config", default="config/ssh.json", help="SSH connection JSON file.")
    parser.add_argument("--operations", default="config/operations.txt", help="Operations text file.")
    parser.add_argument("--no-pause", action="store_true", help="Do not wait for Enter before exit.")
    args = parser.parse_args(argv)
    log_path = create_log_file(Path.cwd())

    try:
        append_log(log_path, "SSH Tool started.")
        ssh_config_path = Path(args.ssh_config)
        operations_path = Path(args.operations)
        ssh_config = load_ssh_config(ssh_config_path)
        operations = load_operations(operations_path)

        print(
            f"Connecting to {ssh_config.username}@{ssh_config.host}:{ssh_config.port} "
            f"({ssh_config.target_os}) ..."
        )
        append_log(log_path, f"Connecting to {ssh_config.username}@{ssh_config.host}:{ssh_config.port} ({ssh_config.target_os})")
        with SshRemote(ssh_config) as remote:
            runner = OperationRunner(remote, target_os=ssh_config.target_os)
            runner.run_all(operations)
        print("All operations completed.")
        append_log(log_path, "All operations completed.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        write_failure_log(log_path, exc)
        print(f"Log written to: {log_path}", file=sys.stderr)
        return 1
    finally:
        if not args.no_pause:
            input("Press Enter to exit...")


if __name__ == "__main__":
    raise SystemExit(main())
