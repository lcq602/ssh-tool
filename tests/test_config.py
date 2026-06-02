from pathlib import Path

import pytest

from ssh_tool.config import CommandOperation, UploadOperation, load_operations, load_ssh_config


def test_load_ssh_config_defaults_to_linux(tmp_path: Path) -> None:
    ssh_file = tmp_path / "ssh.json"
    ssh_file.write_text(
        """
{
  "host": "127.0.0.1",
  "port": 22,
  "username": "root",
  "password": "secret"
}
""",
        encoding="utf-8",
    )

    config = load_ssh_config(ssh_file)

    assert config.target_os == "linux"


def test_load_ssh_config_accepts_windows_target(tmp_path: Path) -> None:
    ssh_file = tmp_path / "ssh.json"
    ssh_file.write_text(
        """
{
  "host": "127.0.0.1",
  "port": 22,
  "username": "Administrator",
  "password": "secret",
  "target_os": "windows"
}
""",
        encoding="utf-8",
    )

    config = load_ssh_config(ssh_file)

    assert config.target_os == "windows"


def test_load_ssh_config_accepts_output_encoding(tmp_path: Path) -> None:
    ssh_file = tmp_path / "ssh.json"
    ssh_file.write_text(
        """
{
  "host": "127.0.0.1",
  "port": 22,
  "username": "Administrator",
  "password": "secret",
  "target_os": "windows",
  "output_encoding": "gbk"
}
""",
        encoding="utf-8",
    )

    config = load_ssh_config(ssh_file)

    assert config.output_encoding == "gbk"


def test_load_ssh_config_rejects_unknown_target_os(tmp_path: Path) -> None:
    ssh_file = tmp_path / "ssh.json"
    ssh_file.write_text(
        """
{
  "host": "127.0.0.1",
  "port": 22,
  "username": "root",
  "password": "secret",
  "target_os": "mac"
}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="target_os"):
        load_ssh_config(ssh_file)


def test_load_operations_skips_comments_and_blank_lines(tmp_path: Path) -> None:
    operations_file = tmp_path / "operations.txt"
    operations_file.write_text(
        """
# comment

cd /home/project/FundValuation
ls -la
""",
        encoding="utf-8",
    )

    operations = load_operations(operations_file)

    assert operations == [
        CommandOperation(command="cd /home/project/FundValuation", line_number=4),
        CommandOperation(command="ls -la", line_number=5),
    ]


def test_load_operations_parses_upload_with_quoted_windows_path(tmp_path: Path) -> None:
    operations_file = tmp_path / "operations.txt"
    operations_file.write_text(
        'upload "D:\\build output\\app.jar" /home/project/FundValuation/app.jar\n',
        encoding="utf-8",
    )

    operations = load_operations(operations_file)

    assert operations == [
        UploadOperation(
            local_path=Path("D:\\build output\\app.jar"),
            remote_path="/home/project/FundValuation/app.jar",
            line_number=1,
        )
    ]


def test_load_operations_rejects_bad_upload_syntax(tmp_path: Path) -> None:
    operations_file = tmp_path / "operations.txt"
    operations_file.write_text("upload only-one-arg\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 1"):
        load_operations(operations_file)
