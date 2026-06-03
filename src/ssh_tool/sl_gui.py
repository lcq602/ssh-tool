"""
Solo Leveling 风格浮动面板 GUI — SSH 工具图形界面
===================================================

提供两个核心类:
    - GuiOutput:      实现与 ConsoleOutput 相同的接口, 但将消息入 queue.Queue
    - SoloLevelingGUI: Tkinter 浮动面板, 暗色 Solo Leveling 主题,
                       从队列读取消息并渲染到 GUI

创建日期: 2026-06-03
迭代: v1.0
"""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable


class GuiOutput:
    """实现 ConsoleOutput 相同接口, 但消息入队列而非直接打印。"""

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


class SoloLevelingGUI:
    """Solo Leveling 风格浮动面板。"""

    # ── 配色 ──────────────────────────────────────────
    BG = "#0d1117"  # 暗夜蓝黑背景
    BG_ALPHA = 0.92  # 透明度
    BORDER_GLOW = "#00bfff"  # 边框发光青蓝
    TITLE_GOLD = "#ffd700"  # 标题亚金
    CMD_CYAN = "#58a6ff"  # 命令文字暗青
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
        self._conn_text.configure(
            text=f"◆  CONNECTING  ● {username}@{host}:{port} ({target_os})"
        )
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

    def run(self) -> None:
        self.root.mainloop()