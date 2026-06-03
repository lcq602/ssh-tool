from __future__ import annotations

import queue

import pytest

from ssh_tool.sl_gui import GuiOutput


class TestGuiOutput:
    def test_header_queues_message(self) -> None:
        q: queue.Queue = queue.Queue()
        out = GuiOutput(q)
        out.header("SSH Tool")
        msg = q.get_nowait()
        assert msg == ("header", "SSH Tool")

    def test_connection_queues_message(self) -> None:
        q: queue.Queue = queue.Queue()
        out = GuiOutput(q)
        out.connection("user", "host", 22, "linux")
        msg = q.get_nowait()
        assert msg == ("connection", "user", "host", 22, "linux")

    def test_info_queues_message(self) -> None:
        q: queue.Queue = queue.Queue()
        out = GuiOutput(q)
        out.info("test info")
        msg = q.get_nowait()
        assert msg == ("info", "test info")

    def test_line_queues_message(self) -> None:
        q: queue.Queue = queue.Queue()
        out = GuiOutput(q)
        out.line("[line 1] $ ls -la")
        msg = q.get_nowait()
        assert msg == ("line", "[line 1] $ ls -la")

    def test_remote_splits_lines(self) -> None:
        q: queue.Queue = queue.Queue()
        out = GuiOutput(q)
        out.remote("line1\nline2")
        msgs = []
        while True:
            try:
                msgs.append(q.get_nowait())
            except queue.Empty:
                break
        assert msgs == [("remote", "line1"), ("remote", "line2")]

    def test_success_queues_message(self) -> None:
        q: queue.Queue = queue.Queue()
        out = GuiOutput(q)
        out.success("All done")
        msg = q.get_nowait()
        assert msg == ("success", "All done")

    def test_error_queues_message(self) -> None:
        q: queue.Queue = queue.Queue()
        out = GuiOutput(q)
        out.error("Something broke", "logs/run.log")
        msg = q.get_nowait()
        assert msg == ("error", "Something broke", "logs/run.log")

    def test_total_steps_queues_message(self) -> None:
        q: queue.Queue = queue.Queue()
        out = GuiOutput(q)
        out.set_total_steps(5)
        msg = q.get_nowait()
        assert msg == ("total_steps", 5)

    def test_update_progress_queues_message(self) -> None:
        q: queue.Queue = queue.Queue()
        out = GuiOutput(q)
        out.update_progress(2, 5)
        msg = q.get_nowait()
        assert msg == ("progress", 2, 5)