from pathlib import Path

from ssh_tool.logging_utils import create_log_file, write_failure_log


def test_create_log_file_uses_logs_directory(tmp_path: Path) -> None:
    log_path = create_log_file(tmp_path, timestamp="20260601-143000")

    assert log_path == tmp_path / "logs" / "run-20260601-143000.log"
    assert log_path.parent.is_dir()


def test_write_failure_log_records_reason_and_traceback(tmp_path: Path) -> None:
    log_path = create_log_file(tmp_path, timestamp="20260601-143000")

    try:
        raise RuntimeError("command failed")
    except RuntimeError as exc:
        write_failure_log(log_path, exc)

    content = log_path.read_text(encoding="utf-8")
    assert "ERROR: command failed" in content
    assert "Traceback" in content
