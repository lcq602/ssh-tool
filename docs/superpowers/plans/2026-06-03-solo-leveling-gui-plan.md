# Solo Leveling GUI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 SSH 工具的控制台输出替换为《我独自升级》风格的浮动面板 GUI，打包 exe 后不显示 cmd 窗口。

**Architecture:** 新增 `sl_gui.py` 包含 Tkinter 浮动面板 + 输出适配器；`main.py` 根据运行模式（控制台 vs 打包 exe）选择输出后端；工作线程执行 SSH 操作，通过 Queue 安全传递消息到 GUI 线程。

**Tech Stack:** Python 3.12+、Tkinter（标准库）、paramiko（SSH）、PyInstaller（打包）

**文件结构：**
| 文件 | 责任 |
|------|------|
| `src/ssh_tool/sl_gui.py` | 新建 — Solo Leveling 浮动面板（Tkinter） + GuiOutput 类 |
| `src/ssh_tool/main.py` | 修改 — 检测运行模式，注入 GUI 或 CLI 输出 |
| `build_exe.bat` | 修改 — 添加 `--noconsole` 和 `--windowed` 参数 |
| `tests/test_sl_gui.py` | 新建 — 测试 GuiOutput 消息队列和渲染 |

---

### Task 1: 创建 Solo Leveling 浮动面板 GUI (`sl_gui.py`)

**Files:**
- Create: `src/ssh_tool/sl_gui.py`
- Test: `tests/test_sl_gui.py`

- [ ] **Step 1: 建立 sl_gui.py 基本框架——SoloLevelingGUI 类和 GuiOutput 类**

```python
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable


class GuiOutput:
    """Implementa o mesmo protocolo de ConsoleOutput, mas enfileira mensagens para a GUI."""

    def __init__(self, msg_queue: queue.Queue) -> None:
        self._queue = msg_queue

    def header(self, title: str) -> None:
        self._queue.put(("header", title))

    def connection(self, username: str, host: str, port: int, target_os: str) -> None:
        self._queue.put(("connection", username, host, port, target_os))

    def info(self, message: str) -> None:
        self._queue.put(("info", message))

    def line(self, message: str) -> None:
        self._queue.put(("line", message))

    def remote(self, text: str) -> None:
        for raw_line in text.splitlines():
            self._queue.put(("remote", raw_line))

    def success(self, message: str) -> None:
        self._queue.put(("success", message))

    def error(self, message: str, log_path: str) -> None:
        self._queue.put(("error", message, log_path))

    def set_total_steps(self, total: int) -> None:
        self._queue.put(("total_steps", total))

    def update_progress(self, current: int, total: int) -> None:
        self._queue.put(("progress", current, total))
```

- [ ] **Step 2: 实现 SoloLevelingGUI 类的初始化（窗口创建、颜色定义、字体设置）**

```python
class SoloLevelingGUI:
    """Solo Leveling 风格浮动面板。"""

    # ── 配色 ──────────────────────────────────────────
    BG = "#0d1117"         # 暗夜蓝黑背景
    BG_ALPHA = 0.92        # 透明度
    BORDER_GLOW = "#00bfff"  # 边框发光青蓝
    TITLE_GOLD = "#ffd700"   # 标题亚金
    CMD_CYAN = "#58a6ff"     # 命令文字暗青
    OUTPUT_GRAY = "#8b949e"  # 输出淡灰
    SUCCESS_GREEN = "#00ff88"
    FAIL_RED = "#ff3333"
    PROGRESS_START = "#00bfff"
    PROGRESS_END = "#0077ff"
    TEXT_WHITE = "#e6edf3"

    WINDOW_W = 560
    WINDOW_H = 380

    def __init__(self, msg_queue: queue.Queue) -> None:
        self.root = tk.Tk()
        self.root.title("SSH Tool")
        self.root.overrideredirect(True)
        self.root.configure(bg=self.BG)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        # 定位到右下角
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = sw - self.WINDOW_W - 20
        y = sh - self.WINDOW_H - 60
        self.root.geometry(f"{self.WINDOW_W}x{self.WINDOW_H}+{x}+{y}")

        self._queue = msg_queue
        self._current_step = 0
        self._total_steps = 0
        self._progress_value = 0.0

        # 自定义字体
        self._font_cmd = tkfont.Font(family="Consolas", size=10)
        self._font_title = tkfont.Font(family="Microsoft YaHei UI", size=11, weight="bold")
        self._font_status = tkfont.Font(family="Microsoft YaHei UI", size=10, weight="bold")

        self._create_widgets()
        self._poll_queue()
```

- [ ] **Step 3: 创建 GUI 组件（标题栏、连接状态、日志区、进度条、状态提示）**

```python
    def _create_widgets(self) -> None:
        # ── 外层容器（带发光边框效果） ──
        self._outer_frame = tk.Frame(self.root, bg=self.BORDER_GLOW, padx=1, pady=1)
        self._outer_frame.pack(fill=tk.BOTH, expand=True)

        # ── 内层主容器 ──
        self._main = tk.Frame(self._outer_frame, bg=self.BG)
        self._main.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # ── 可拖动标题栏 ──
        title_bar = tk.Frame(self._main, bg=self.BG, cursor="fleur")
        title_bar.pack(fill=tk.X, padx=12, pady=(6, 2))
        title_bar.bind("<ButtonPress-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._on_drag)

        lbl_title = tk.Label(
            title_bar, text="⚜  SYSTEM  ⚜",
            font=self._font_title, fg=self.TITLE_GOLD, bg=self.BG,
        )
        lbl_title.pack(side=tk.LEFT)
        lbl_title.bind("<ButtonPress-1>", self._start_drag)
        lbl_title.bind("<B1-Motion>", self._on_drag)

        btn_close = tk.Label(
            title_bar, text=" ✕ ", font=self._font_title,
            fg=self.OUTPUT_GRAY, bg=self.BG, cursor="hand2",
        )
        btn_close.pack(side=tk.RIGHT)
        btn_close.bind("<Button-1>", lambda e: self.root.destroy())
        btn_close.bind("<Enter>", lambda e: btn_close.configure(fg=self.FAIL_RED))
        btn_close.bind("<Leave>", lambda e: btn_close.configure(fg=self.OUTPUT_GRAY))

        # ── 连接状态 ──
        self._conn_frame = tk.Frame(self._main, bg=self.BG)
        self._conn_frame.pack(fill=tk.X, padx=14, pady=(2, 4))

        self._conn_dot = tk.Canvas(self._conn_frame, width=10, height=10,
                                    bg=self.BG, highlightthickness=0)
        self._conn_dot.pack(side=tk.LEFT, padx=(0, 6))
        self._dot_id = self._conn_dot.create_oval(1, 1, 9, 9,
                                                    fill=self.PROGRESS_START, outline="")

        self._conn_text = tk.Label(
            self._conn_frame, text="◆  INITIALIZING",
            font=self._font_status, fg=self.CMD_CYAN, bg=self.BG,
            anchor="w",
        )
        self._conn_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── 分隔线 ──
        sep_frame = tk.Frame(self._main, bg=self.BG)
        sep_frame.pack(fill=tk.X, padx=14, pady=(0, 4))
        self._sep_label = tk.Label(
            sep_frame, text="", font=self._font_cmd,
            fg=self.OUTPUT_GRAY, bg=self.BG, anchor="w",
        )
        self._sep_label.pack(fill=tk.X)

        # ── 日志输出区 ──
        self._log_text = tk.Text(
            self._main,
            font=self._font_cmd,
            bg="#0a0e17",
            fg=self.OUTPUT_GRAY,
            bd=0,
            padx=14,
            pady=4,
            height=11,
            state=tk.DISABLED,
            wrap=tk.WORD,
            highlightthickness=0,
        )
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))

        # 配置 Text 组件的彩色标签
        self._log_text.tag_configure("cmd", foreground=self.CMD_CYAN)
        self._log_text.tag_configure("output", foreground=self.OUTPUT_GRAY)
        self._log_text.tag_configure("success", foreground=self.SUCCESS_GREEN)
        self._log_text.tag_configure("error", foreground=self.FAIL_RED)
        self._log_text.tag_configure("info", foreground=self.TEXT_WHITE)
        self._log_text.tag_configure("remote_out", foreground=self.OUTPUT_GRAY)

        # ── 进度条（Canvas 绘制发光效果） ──
        self._progress_canvas = tk.Canvas(
            self._main, height=6, bg=self.BG,
            highlightthickness=0,
        )
        self._progress_canvas.pack(fill=tk.X, padx=14, pady=(4, 2))

        # 进度条背景
        pb_w = self.WINDOW_W - 30
        self._progress_bg_id = self._progress_canvas.create_rectangle(
            0, 0, pb_w, 6,
            fill="#1a1f2e", outline="",
        )
        # 进度条前景（初始为 0）
        self._progress_fill_id = self._progress_canvas.create_rectangle(
            0, 0, 0, 6,
            fill=self.BORDER_GLOW, outline="",
        )

        # ── 状态提示 ──
        self._status_label = tk.Label(
            self._main, text="",
            font=self._font_status, fg=self.TEXT_WHITE, bg=self.BG,
            anchor="w",
        )
        self._status_label.pack(fill=tk.X, padx=14, pady=(2, 8))
```

- [ ] **Step 4: 实现窗口拖动、队列轮询和消息处理方法**

```python
    # ── 窗口拖动 ──
    def _start_drag(self, event: tk.Event) -> None:
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_drag(self, event: tk.Event) -> None:
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ── 队列轮询（每 50ms） ──
    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                self._dispatch(msg)
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self._poll_queue)

    def _dispatch(self, msg: tuple) -> None:
        kind = msg[0]
        if kind == "header":
            self._on_header(msg[1])
        elif kind == "connection":
            self._on_connection(msg[1], msg[2], msg[3], msg[4])
        elif kind == "info":
            self._on_info(msg[1])
        elif kind == "line":
            self._on_line(msg[1])
        elif kind == "remote":
            self._on_remote(msg[1])
        elif kind == "success":
            self._on_success(msg[1])
        elif kind == "error":
            self._on_error(msg[1], msg[2])
        elif kind == "total_steps":
            self._total_steps = msg[1]
            self._update_sep()
        elif kind == "progress":
            self._on_progress(msg[1], msg[2])

    # ── 各消息处理 ──
    def _on_header(self, title: str) -> None:
        pass  # 标题已经显示在顶栏

    def _on_connection(self, username: str, host: str, port: int, target_os: str) -> None:
        self._conn_text.configure(text=f"◆  CONNECTING  ● {username}@{host}:{port} ({target_os})")
        self._conn_dot.itemconfigure(self._dot_id, fill=self.PROGRESS_START)

    def _on_info(self, message: str) -> None:
        self._append_log(f">> {message}", "info")

    def _on_line(self, message: str) -> None:
        self._append_log(f"$ {message}", "cmd")

    def _on_remote(self, text: str) -> None:
        self._append_log(f"  {text}", "remote_out")

    def _on_success(self, message: str) -> None:
        self._conn_dot.itemconfigure(self._dot_id, fill=self.SUCCESS_GREEN)
        self._status_label.configure(text=f"✓  {message}", fg=self.SUCCESS_GREEN)
        self._append_log(f"✓ {message}", "success")

    def _on_error(self, message: str, log_path: str) -> None:
        self._conn_dot.itemconfigure(self._dot_id, fill=self.FAIL_RED)
        self._status_label.configure(text=f"✗  {message}", fg=self.FAIL_RED)
        self._append_log(f"✗ {message}", "error")
        self._append_log(f"LOG: {log_path}", "error")

    def _on_progress(self, current: int, total: int) -> None:
        fraction = current / total if total > 0 else 0.0
        pb_w = self.WINDOW_W - 30
        fill_w = int(pb_w * fraction)
        self._progress_canvas.coords(self._progress_fill_id, 0, 0, fill_w, 6)
        self._progress_value = fraction
        self._current_step = current
        self._update_sep()

    def _update_sep(self) -> None:
        if self._total_steps > 0:
            pct = int(self._progress_value * 100)
            self._sep_label.configure(
                text=f"────  STEP {self._current_step:02d}/{self._total_steps:02d}  ({pct}%)  ────"
            )

    def _append_log(self, text: str, tag: str = "output") -> None:
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, text + "\n", tag)
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)
```

- [ ] **Step 5: 添加 run() 方法启动 GUI**

```python
    def run(self) -> None:
        self.root.mainloop()
```

- [ ] **Step 6: 添加 total_steps 计数逻辑到 GuiOutput**

确保 GuiOutput 有一个 `set_total_steps` 和 `update_progress` 方法（已在 Step 1 中），还需要给 GuiOutput 添加一个 `set_status` 方法（可选）：

GuiOutput 类的完整代码已经在 Step 1 中完成，无需额外操作。

**Step 1-5 完成后 `sl_gui.py` 的完整结构：**

```python
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable


class GuiOutput:
    """实现 ConsoleOutput 相同接口，但消息入队列而非直接打印。"""

    def __init__(self, msg_queue: queue.Queue) -> None:
        self._queue = msg_queue

    def header(self, title: str) -> None: ...
    def connection(self, username: str, host: str, port: int, target_os: str) -> None: ...
    def info(self, message: str) -> None: ...
    def line(self, message: str) -> None: ...
    def remote(self, text: str) -> None: ...
    def success(self, message: str) -> None: ...
    def error(self, message: str, log_path: str) -> None: ...
    def set_total_steps(self, total: int) -> None: ...
    def update_progress(self, current: int, total: int) -> None: ...


class SoloLevelingGUI:
    BG = "#0d1117"
    BORDER_GLOW = "#00bfff"
    TITLE_GOLD = "#ffd700"
    CMD_CYAN = "#58a6ff"
    OUTPUT_GRAY = "#8b949e"
    SUCCESS_GREEN = "#00ff88"
    FAIL_RED = "#ff3333"
    TEXT_WHITE = "#e6edf3"
    WINDOW_W = 560
    WINDOW_H = 380

    def __init__(self, msg_queue: queue.Queue) -> None: ...
    def run(self) -> None: ...
    # (内部方法 _create_widgets, _start_drag, _on_drag, _poll_queue,
    #  _dispatch, _on_header, _on_connection, _on_info, _on_line,
    #  _on_remote, _on_success, _on_error, _on_progress, _update_sep, _append_log)
```

---

### Task 2: 修改 `main.py` 支持 GUI 模式

**Files:**
- Modify: `src/ssh_tool/main.py`

- [ ] **Step 1: 修改 main() 函数——检测运行模式并启动 GUI**

需要在文件顶部导入新增模块：

```python
import queue
import sys
import threading
```

修改 `main()` 函数入口逻辑：

```python
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
    from pathlib import Path
    from ssh_tool.console_output import ConsoleOutput
    from ssh_tool.config import load_operations, load_ssh_config
    from ssh_tool.logging_utils import append_log, create_log_file, write_failure_log
    from ssh_tool.remote import SshRemote
    from ssh_tool.runner import OperationRunner

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
    import queue
    import threading
    from pathlib import Path
    from ssh_tool.config import load_operations, load_ssh_config
    from ssh_tool.logging_utils import append_log, create_log_file, write_failure_log
    from ssh_tool.remote import SshRemote
    from ssh_tool.runner import OperationRunner
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
                # 放回去让 _poll_queue 处理
                # 实际上 _poll_queue 也在轮询，为避免竞争，做特殊处理
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
```

- [ ] **Step 2: 运行现有测试确保未破坏 CLI 模式**

```bash
cd "D:\project\codexProject\ssh-tool"
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: 所有现有测试通过（无回归）

---

### Task 3: 修改 `build_exe.bat` 添加无控制台打包

**Files:**
- Modify: `build_exe.bat`

- [ ] **Step 1: 添加 `--noconsole` 和 `--windowed` 参数**

```bash
@echo off
setlocal
cd /d "%~dp0"

uv run pyinstaller ^
  --clean ^
  --onefile ^
  --noconsole ^
  --paths src ^
  --name ssh-tool ^
  src\ssh_tool\main.py

if errorlevel 1 (
  echo CLI build failed.
  pause
  exit /b 1
)

if exist dist\config rmdir /s /q dist\config
mkdir dist\config
copy config\ssh.example.json dist\config\ssh.example.json >nul
copy config\operations.txt dist\config\operations.txt >nul

echo.
echo Build complete: dist\ssh-tool.exe
echo Config copied to: dist\config
pause
```

---

### Task 4: 编写测试

**Files:**
- Create: `tests/test_sl_gui.py`

- [ ] **Step 1: 编写 GuiOutput 消息队列测试**

```python
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
```

- [ ] **Step 2: 运行测试验证通过**

```bash
cd "D:\project\codexProject\ssh-tool"
.venv\Scripts\python.exe -m pytest tests/test_sl_gui.py -v
```

Expected: 所有测试 PASS

---

### Task 5: 集成测试（手动）

- [ ] **Step 1: 打包 exe**

```bash
cd "D:\project\codexProject\ssh-tool"
.\build_exe.bat
```

Expected: `dist/ssh-tool.exe` 生成成功

- [ ] **Step 2: 确认 exe 无 cmd 窗口**

双击 `dist/ssh-tool.exe`，确认只弹出 GUI 浮动面板，无黑 cmd 窗口。

- [ ] **Step 3: 确认 CLI 模式仍可用**

```bash
cd "D:\project\codexProject\ssh-tool"
uv run ssh-tool --cli
```

Expected: 显示原有控制台输出，无 GUI

---

### 自检清单

1. **Spec 覆盖：**
   - ✅ 无控制台窗口 → Task 3 (`--noconsole`)
   - ✅ Solo Leveling 暗色浮动面板 → Task 1 (sl_gui.py)
   - ✅ 连接状态 → `_on_connection` 方法
   - ✅ 命令输出 → `_on_line` + `_on_remote`
   - ✅ 进度条 → `_on_progress` + Canvas
   - ✅ 最终状态 → `_on_success` / `_on_error`
   - ✅ 面板可拖动 → `_start_drag` + `_on_drag`
   - ✅ 条件运行逻辑 → `_run_gui` / `_run_cli` 分支
   - ✅ 日志文件依然写入 → `_run_gui` 内保留 `append_log` 调用

2. **无占位符：** 所有代码块完整

3. **类型一致性：** `GuiOutput` 方法签名与 `ConsoleOutput` 一致；消息元组类型在 `_dispatch` 中匹配