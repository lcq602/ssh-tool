from ssh_tool.remote import decode_output


def test_decode_output_auto_handles_windows_gbk_bytes() -> None:
    data = "驱动器 C 中的卷没有标签".encode("gbk")

    assert decode_output(data, output_encoding="auto", target_os="windows") == "驱动器 C 中的卷没有标签"


def test_decode_output_auto_handles_linux_utf8_bytes() -> None:
    data = "total 12\n项目\n".encode("utf-8")

    assert decode_output(data, output_encoding="auto", target_os="linux") == "total 12\n项目\n"


def test_decode_output_replaces_bad_bytes_as_last_resort() -> None:
    data = b"\xff\xfe"

    assert "\ufffd" in decode_output(data, output_encoding="utf-8", target_os="linux")
