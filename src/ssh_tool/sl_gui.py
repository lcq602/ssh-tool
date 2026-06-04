"""
Solo Leveling 风格浮动面板 GUI — SSH 工具图形界面
===================================================

提供两个核心类:
    - GuiOutput:      实现与 ConsoleOutput 相同的接口, 但将消息入 queue.Queue
    - SoloLevelingGUI: Tkinter 浮动面板, 暗色 Solo Leveling 主题,
                       从队列读取消息并渲染到 GUI

创建日期: 2026-06-03
迭代: v2.0
修改日期: 2026-06-04
修改内容: 新增步骤列表面板 + 中英文双语言支持 + 运行步骤动画
"""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable

from ssh_tool.l10n import L10n, get_l10n


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

    def step_item(self, index: int, text: str, status: str) -> None:
        """添加一个步骤项到队列。

        Args:
            index: 步骤序号。
            text:  步骤描述文本。
            status: 步骤状态, 可选 "pending" / "running" / "done" / "error"。
        """
        self._queue.put(("step_item", index, text, status))


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
    WINDOW_H = 480

    SPINNER_CHARS = ["⟳", "/", "—", "\\"]

    def __init__(self, msg_queue: queue.Queue, l10n: L10n | None = None) -> None:
        self.root = tk.Tk()
        self.root.title("SSH Tool")
        self.root.overrideredirect(True)
        self.root.configure(bg=self.BG)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        # 居中显示
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - self.WINDOW_W) // 2
        y = (sh - self.WINDOW_H) // 2
        self.root.geometry(f"{self.WINDOW_W}x{self.WINDOW_H}+{x}+{y}")

        self._queue = msg_queue
        self._current_step = 0
        self._total_steps = 0
        self._progress_value = 0.0

        # 语言支持
        self._l10n = l10n or get_l10n()

        # 步骤列表数据
        self._steps: list[dict] = []
        self._step_rotation_index = 0
        self._running_step_index: int | None = None

        # 自定义字体
        self._font_cmd = tkfont.Font(family="Consolas", size=10)
        self._font_title = tkfont.Font(family="Microsoft YaHei UI", size=11, weight="bold")
        self._font_status = tkfont.Font(family="Microsoft YaHei UI", size=10, weight="bold")

        self._create_widgets()
        self._poll_queue()
        self.root.after(500, self._animate_step_icons)

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
            title_bar, text=self._l10n.title,
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
            self._conn_frame, text=self._l10n.initializing,
            font=self._font_status, fg=self.CMD_CYAN, bg=self.BG,
            anchor="w",
        )
        self._conn_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── 步骤列表（可滚动） ──
        self._step_container = tk.Frame(self._main, bg=self.BG)
        self._step_container.pack(fill=tk.BOTH, expand=True, padx=14, pady=(2, 2))

        self._step_canvas = tk.Canvas(
            self._step_container, bg=self.BG, highlightthickness=0,
            bd=0, height=200,
        )
        self._step_scrollbar = tk.Scrollbar(
            self._step_container, orient=tk.VERTICAL,
            command=self._step_canvas.yview,
        )
        self._step_canvas.configure(yscrollcommand=self._step_scrollbar.set)

        self._step_inner = tk.Frame(self._step_canvas, bg=self.BG)
        self._step_canvas_window = self._step_canvas.create_window(
            (0, 0), window=self._step_inner, anchor="nw", tags="inner"
        )

        def _configure_step_inner(event: tk.Event) -> None:
            self._step_canvas.configure(scrollregion=self._step_canvas.bbox("all"))
            self._step_canvas.itemconfig("inner", width=event.width)

        self._step_inner.bind("<Configure>", _configure_step_inner)
        self._step_canvas.bind("<Configure>", _configure_step_inner)

        def _on_mousewheel(event: tk.Event) -> None:
            self._step_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self._step_canvas.bind("<MouseWheel>", _on_mousewheel)

        self._step_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._step_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ── 日志输出区（精简） ──
        self._log_text = tk.Text(
            self._main,
            font=self._font_cmd,
            bg="#0a0e17",
            fg=self.OUTPUT_GRAY,
            bd=0,
            padx=14,
            pady=4,
            height=4,
            state=tk.DISABLED,
            wrap=tk.WORD,
            highlightthickness=0,
        )
        self._log_text.pack(fill=tk.X, padx=2, pady=(2, 2))

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
        elif kind == "progress":
            self._on_progress(msg[1], msg[2])
        elif kind == "step_item":
            self._on_step_item(msg[1], msg[2], msg[3])

    # ── 各消息处理 ──
    def _on_header(self, title: str) -> None:
        pass  # 标题已经显示在顶栏

    def _on_connection(self, username: str, host: str, port: int, target_os: str) -> None:
        self._conn_text.configure(
            text=self._l10n.connecting.format(
                user=username, host=host, port=port, os=target_os
            )
        )
        self._conn_dot.itemconfigure(self._dot_id, fill=self.PROGRESS_START)

    def _on_info(self, message: str) -> None:
        self._append_log(self._l10n.log_info.format(msg=message), "info")

    def _on_line(self, message: str) -> None:
        self._append_log(self._l10n.log_cmd.format(msg=message), "cmd")

    def _on_remote(self, text: str) -> None:
        self._append_log(self._l10n.log_remote.format(text=text), "remote_out")

    def _on_success(self, message: str) -> None:
        self._conn_dot.itemconfigure(self._dot_id, fill=self.SUCCESS_GREEN)
        self._status_label.configure(text=self._l10n.all_done, fg=self.SUCCESS_GREEN)
        self._append_log(f"✓ {message}", "success")

    def _on_error(self, message: str, log_path: str) -> None:
        self._conn_dot.itemconfigure(self._dot_id, fill=self.FAIL_RED)
        self._status_label.configure(
            text=self._l10n.error_prefix.format(msg=message), fg=self.FAIL_RED
        )
        self._append_log(self._l10n.error_prefix.format(msg=message), "error")
        self._append_log(self._l10n.log_error.format(path=log_path), "error")

    def _on_progress(self, current: int, total: int) -> None:
        fraction = current / total if total > 0 else 0.0
        pb_w = self.WINDOW_W - 30
        fill_w = int(pb_w * fraction)
        self._progress_canvas.coords(self._progress_fill_id, 0, 0, fill_w, 6)
        self._progress_value = fraction
        self._current_step = current

        # 更新步骤状态：前一步 → done，当前步 → running
        if self._steps:
            prev_idx = current - 2  # 0-indexed, current 是 1-indexed
            run_idx = current - 1
            if 0 <= prev_idx < len(self._steps):
                self._steps[prev_idx]["status"] = "done"
            if 0 <= run_idx < len(self._steps):
                self._steps[run_idx]["status"] = "running"
                self._running_step_index = run_idx
            else:
                self._running_step_index = None
            self._rebuild_step_list()

    # ── 步骤列表方法 ──
    def _on_step_item(self, index: int, text: str, status: str) -> None:
        """处理 step_item 消息：添加或更新步骤。"""
        while len(self._steps) <= index:
            self._steps.append({"text": "", "status": "pending"})

        self._steps[index] = {"text": text, "status": status}
        self._rebuild_step_list()

    def _rebuild_step_list(self) -> None:
        """根据 self._steps 数据重建所有步骤行。"""
        for widget in self._step_inner.winfo_children():
            widget.destroy()

        colors = {
            "pending": self.OUTPUT_GRAY,
            "running": self.CMD_CYAN,
            "done": self.SUCCESS_GREEN,
            "error": self.FAIL_RED,
        }

        for i, step in enumerate(self._steps):
            row = tk.Frame(self._step_inner, bg=self.BG)
            row.pack(fill=tk.X, pady=(1, 1))

            icon_text, _ = self._step_icon_and_color(step["status"])
            fg_color = colors.get(step["status"], self.OUTPUT_GRAY)

            lbl_icon = tk.Label(
                row, text=icon_text, font=self._font_cmd,
                fg=fg_color, bg=self.BG, width=3, anchor="w",
            )
            lbl_icon.pack(side=tk.LEFT)

            lbl_text = tk.Label(
                row, text=step["text"], font=self._font_cmd,
                fg=fg_color, bg=self.BG, anchor="w",
            )
            lbl_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

            step["_icon_label"] = lbl_icon

    @staticmethod
    def _step_icon_and_color(status: str) -> tuple[str, str]:
        icons_map = {
            "pending": ("⏳", "#8b949e"),
            "running": ("⟳", "#00bfff"),
            "done": ("✅", "#00ff88"),
            "error": ("❌", "#ff3333"),
        }
        return icons_map.get(status, ("⏳", "#8b949e"))

    def _animate_step_icons(self) -> None:
        """每 500ms 旋转当前运行步骤的图标。"""
        if self._running_step_index is not None:
            self._step_rotation_index = (self._step_rotation_index + 1) % len(self.SPINNER_CHARS)
            char = self.SPINNER_CHARS[self._step_rotation_index]
            if self._running_step_index < len(self._steps):
                step = self._steps[self._running_step_index]
                icon_label = step.get("_icon_label")
                if icon_label:
                    icon_label.configure(text=char)

        self.root.after(500, self._animate_step_icons)

    # ── 辅助方法 ──
    def _append_log(self, text: str, tag: str = "output") -> None:
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, text + "\n", tag)
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def run(self) -> None:
        self.root.mainloop()