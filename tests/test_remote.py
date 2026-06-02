from ssh_tool.remote import decode_output
from ssh_tool.remote import SshRemote
from ssh_tool.config import SshConfig


def test_decode_output_auto_handles_windows_gbk_bytes() -> None:
    data = "驱动器 C 中的卷没有标签".encode("gbk")

    assert decode_output(data, output_encoding="auto", target_os="windows") == "驱动器 C 中的卷没有标签"


def test_decode_output_auto_handles_linux_utf8_bytes() -> None:
    data = "total 12\n项目\n".encode("utf-8")

    assert decode_output(data, output_encoding="auto", target_os="linux") == "total 12\n项目\n"


def test_decode_output_replaces_bad_bytes_as_last_resort() -> None:
    data = b"\xff\xfe"

    assert "\ufffd" in decode_output(data, output_encoding="utf-8", target_os="linux")


def test_ssh_remote_rejects_unknown_host_keys_by_default(monkeypatch) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.policy = None

        def load_system_host_keys(self) -> None:
            pass

        def set_missing_host_key_policy(self, policy) -> None:
            self.policy = policy

        def connect(self, **kwargs) -> None:
            pass

        def close(self) -> None:
            pass

    fake_client = FakeClient()
    monkeypatch.setattr("ssh_tool.remote.paramiko.SSHClient", lambda: fake_client)

    config = SshConfig(host="example.com", port=22, username="deploy", password="secret")
    with SshRemote(config):
        pass

    assert fake_client.policy.__class__.__name__ == "RejectPolicy"
