from __future__ import annotations

import pytest

from ssh_tool.l10n import L10n, detect_language, get_l10n


class TestDetectLanguage:
    def test_returns_string(self) -> None:
        lang = detect_language()
        assert lang in ("zh", "en")


class TestGetL10n:
    def test_en_returns_english_defaults(self) -> None:
        l10n = get_l10n("en")
        assert l10n.lang == "en"
        assert l10n.title == "⚜  SYSTEM  ⚜"
        assert l10n.initializing == "◆  INITIALIZING"
        assert l10n.all_done == "✓ All operations completed."

    def test_zh_returns_chinese(self) -> None:
        l10n = get_l10n("zh")
        assert l10n.lang == "zh"
        assert "系统" in l10n.title
        assert "初始化" in l10n.initializing
        assert "所有操作已完成" in l10n.all_done

    def test_connecting_format_en(self) -> None:
        l10n = get_l10n("en")
        text = l10n.connecting.format(user="root", host="10.0.0.1", port=22, os="linux")
        assert "root@10.0.0.1:22" in text
        assert "linux" in text

    def test_connecting_format_zh(self) -> None:
        l10n = get_l10n("zh")
        text = l10n.connecting.format(user="admin", host="192.168.1.1", port=2222, os="windows")
        assert "admin@192.168.1.1:2222" in text
        assert "windows" in text

    def test_error_prefix_format(self) -> None:
        l10n = get_l10n("en")
        text = l10n.error_prefix.format(msg="Connection refused")
        assert text == "✗ Connection refused"

    def test_log_info_format(self) -> None:
        l10n = get_l10n("en")
        text = l10n.log_info.format(msg="test message")
        assert text == ">> test message"

    def test_log_error_format_en(self) -> None:
        l10n = get_l10n("en")
        text = l10n.log_error.format(path="logs/run.log")
        assert text == "LOG: logs/run.log"

    def test_log_error_format_zh(self) -> None:
        l10n = get_l10n("zh")
        text = l10n.log_error.format(path="logs/run.log")
        assert text == "日志: logs/run.log"

    def test_frozen_dataclass(self) -> None:
        l10n = get_l10n("en")
        assert isinstance(l10n, L10n)
        # 验证 L10n 是 frozen dataclass
        with pytest.raises(AttributeError):
            l10n.title = "modified"  # type: ignore[misc]