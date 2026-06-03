from pathlib import Path

from ssh_tool.config import CommandOperation, UploadOperation
from ssh_tool.runner import OperationRunner


class FakeRemote:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.uploads: list[tuple[Path, str]] = []

    def run(self, command: str) -> int:
        self.commands.append(command)
        return 0

    def upload(self, local_path: Path, remote_path: str) -> None:
        self.uploads.append((local_path, remote_path))


def test_runner_keeps_cd_state_for_following_commands() -> None:
    remote = FakeRemote()
    runner = OperationRunner(remote, target_os="linux")

    runner.run_all(
        [
            CommandOperation("cd /home/project/FundValuation", 1),
            CommandOperation("ls -la", 2),
            CommandOperation("./start.sh stop", 3),
        ]
    )

    assert remote.commands == [
        "cd /home/project/FundValuation && ls -la",
        "cd /home/project/FundValuation && ./start.sh stop",
    ]


def test_runner_uploads_files_without_wrapping_as_command(tmp_path: Path) -> None:
    remote = FakeRemote()
    runner = OperationRunner(remote, target_os="linux")
    local_file = tmp_path / "app.jar"

    runner.run_all(
        [
            UploadOperation(local_file, "/home/project/FundValuation/app.jar", 1),
        ]
    )

    assert remote.commands == []
    assert remote.uploads == [(local_file, "/home/project/FundValuation/app.jar")]


def test_runner_uses_windows_cd_for_windows_target() -> None:
    remote = FakeRemote()
    runner = OperationRunner(remote, target_os="windows")

    runner.run_all(
        [
            CommandOperation("cd C:\\deploy\\FundValuation", 1),
            CommandOperation("dir", 2),
            CommandOperation("start.bat stop", 3),
        ]
    )

    assert remote.commands == [
        'cd /d "C:\\deploy\\FundValuation" && dir',
        'cd /d "C:\\deploy\\FundValuation" && start.bat stop',
    ]


def test_runner_resolves_relative_windows_cd() -> None:
    remote = FakeRemote()
    runner = OperationRunner(remote, target_os="windows")

    runner.run_all(
        [
            CommandOperation("cd C:\\deploy", 1),
            CommandOperation("cd FundValuation", 2),
            CommandOperation("dir", 3),
        ]
    )

    assert remote.commands == [
        'cd /d "C:\\deploy\\FundValuation" && dir',
    ]


def test_runner_waits_for_each_command_before_starting_next() -> None:
    events: list[str] = []

    class OrderedRemote:
        def run(self, command: str) -> int:
            events.append(f"start:{command}")
            events.append(f"finish:{command}")
            return 0

        def upload(self, local_path: Path, remote_path: str) -> None:
            events.append(f"upload:{remote_path}")

    runner = OperationRunner(OrderedRemote(), target_os="linux")

    runner.run_all(
        [
            CommandOperation("echo one", 1),
            CommandOperation("echo two", 2),
        ]
    )

    assert events == [
        "start:echo one",
        "finish:echo one",
        "start:echo two",
        "finish:echo two",
    ]


def test_runner_sends_progress_to_output_callback() -> None:
    messages: list[str] = []
    remote = FakeRemote()
    runner = OperationRunner(remote, target_os="linux", output=messages.append)

    runner.run_all(
        [
            CommandOperation("cd /home/project/app", 1),
            CommandOperation("ls -la", 2),
        ]
    )

    assert messages == [
        "[line 1] current directory: /home/project/app",
        "[line 2] $ cd /home/project/app && ls -la",
    ]
