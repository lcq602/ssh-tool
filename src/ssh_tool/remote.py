from __future__ import annotations

from pathlib import Path

import paramiko

from ssh_tool.config import SshConfig, TargetOs


class SshRemote:
    def __init__(self, config: SshConfig) -> None:
        self.config = config
        self._client: paramiko.SSHClient | None = None

    def __enter__(self) -> "SshRemote":
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.username,
            password=self.config.password,
            timeout=self.config.timeout,
            banner_timeout=self.config.timeout,
            auth_timeout=self.config.timeout,
        )
        self._client = client
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore[no-untyped-def]
        if self._client is not None:
            self._client.close()

    def run(self, command: str) -> int:
        client = self._require_client()
        stdin, stdout, stderr = client.exec_command(command)
        stdin.close()

        stdout_text = decode_output(stdout.read(), self.config.output_encoding, self.config.target_os)
        stderr_text = decode_output(stderr.read(), self.config.output_encoding, self.config.target_os)
        if stdout_text:
            print(stdout_text, end="")
        if stderr_text:
            print(stderr_text, end="")

        return stdout.channel.recv_exit_status()

    def upload(self, local_path: Path, remote_path: str) -> None:
        client = self._require_client()
        if not local_path.is_file():
            raise FileNotFoundError(f"Local file does not exist: {local_path}")

        with client.open_sftp() as sftp:
            sftp.put(str(local_path), remote_path)

    def _require_client(self) -> paramiko.SSHClient:
        if self._client is None:
            raise RuntimeError("SSH client is not connected")
        return self._client


def decode_output(data: bytes | str, output_encoding: str, target_os: TargetOs) -> str:
    if isinstance(data, str):
        return data

    encodings = _candidate_encodings(output_encoding, target_os)
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode(encodings[0], errors="replace")


def _candidate_encodings(output_encoding: str, target_os: TargetOs) -> list[str]:
    if output_encoding != "auto":
        return [output_encoding]
    if target_os == "windows":
        return ["gbk", "cp936", "utf-8"]
    return ["utf-8", "gbk", "cp936"]
