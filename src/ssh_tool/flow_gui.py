from __future__ import annotations

import itertools
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ssh_tool.config import load_operations, load_ssh_config
from ssh_tool.operation_flow import FlowEdge, FlowNode, OperationFlow
from ssh_tool.remote import SshRemote
from ssh_tool.runner import OperationRunner


NODE_WIDTH = 180
NODE_HEIGHT = 58
FLOW_PATH = Path("config/operations.flow.json")
OPERATIONS_PATH = Path("config/operations.txt")


class FlowEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SSH Operations Flow Editor")
        self.geometry("1100x700")
        self.minsize(900, 560)

        self.nodes: dict[str, FlowNode] = {}
        self.edges: list[FlowEdge] = []
        self.node_items: dict[str, tuple[int, int]] = {}
        self.edge_items: dict[tuple[str, str], int] = {}
        self.selected_node_id: str | None = None
        self.drag_node_id: str | None = None
        self.drag_offset = (0, 0)
        self.connect_source_id: str | None = None
        self.id_counter = itertools.count(1)

        self.command_var = tk.StringVar()
        self.local_path_var = tk.StringVar()
        self.remote_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪")
        self.run_state_var = tk.StringVar(value="未运行")
        self.output_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.is_running = False

        self._configure_style()
        self._build_layout()
        self._load_or_create_default_flow()
        self._redraw()
        self.after(100, self._drain_output_queue)

    def _configure_style(self) -> None:
        self.configure(bg="#111827")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#111827")
        style.configure("Panel.TFrame", background="#182230")
        style.configure("Tool.TButton", padding=(12, 8), font=("Microsoft YaHei UI", 9))
        style.configure("Primary.TButton", padding=(12, 9), font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Panel.TLabel", background="#182230", foreground="#d0d5dd", font=("Microsoft YaHei UI", 9))
        style.configure("Title.TLabel", background="#182230", foreground="#f9fafb", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Status.TLabel", background="#111827", foreground="#98a2b3", font=("Microsoft YaHei UI", 9))

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="App.TFrame", padding=(14, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="SSH Flow Console", style="Status.TLabel", font=("Microsoft YaHei UI", 15, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.run_state_var, style="Status.TLabel").grid(row=0, column=1, sticky="e")

        body = ttk.Frame(self, style="App.TFrame", padding=(12, 0, 12, 12))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=0)

        toolbar = ttk.Frame(body, style="Panel.TFrame", padding=12)
        toolbar.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        ttk.Label(toolbar, text="流程控件", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(toolbar, text="添加命令", style="Tool.TButton", command=self.add_command_node).grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(toolbar, text="添加上传", style="Tool.TButton", command=self.add_upload_node).grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(toolbar, text="连接箭头", style="Tool.TButton", command=self.start_connect_mode).grid(row=3, column=0, sticky="ew", pady=(16, 0))
        ttk.Button(toolbar, text="删除选中", style="Tool.TButton", command=self.delete_selected).grid(row=4, column=0, sticky="ew", pady=(6, 0))
        ttk.Separator(toolbar).grid(row=5, column=0, sticky="ew", pady=16)
        ttk.Button(toolbar, text="保存流程", style="Tool.TButton", command=self.save_flow).grid(row=6, column=0, sticky="ew")
        ttk.Button(toolbar, text="加载流程", style="Tool.TButton", command=self.load_flow_dialog).grid(row=7, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(toolbar, text="写入 operations.txt", style="Tool.TButton", command=self.write_operations).grid(row=8, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(toolbar, text="运行流程", style="Primary.TButton", command=self.run_operations).grid(row=9, column=0, sticky="ew", pady=(18, 0))

        main = ttk.Frame(body, style="Panel.TFrame", padding=8)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(main, bg="#202b3c", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        inspector = ttk.Frame(body, style="Panel.TFrame", padding=12)
        inspector.grid(row=0, column=2, sticky="ns", padx=(10, 0))
        inspector.columnconfigure(0, weight=1)
        ttk.Label(inspector, text="选中节点", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(inspector, text="命令", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.command_entry = ttk.Entry(inspector, textvariable=self.command_var, width=34)
        self.command_entry.grid(row=2, column=0, sticky="ew")
        ttk.Label(inspector, text="本地路径", style="Panel.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.local_entry = ttk.Entry(inspector, textvariable=self.local_path_var, width=34)
        self.local_entry.grid(row=4, column=0, sticky="ew")
        ttk.Label(inspector, text="远程路径", style="Panel.TLabel").grid(row=5, column=0, sticky="w", pady=(12, 0))
        self.remote_entry = ttk.Entry(inspector, textvariable=self.remote_path_var, width=34)
        self.remote_entry.grid(row=6, column=0, sticky="ew")
        ttk.Button(inspector, text="应用修改", style="Tool.TButton", command=self.apply_selected_edits).grid(row=7, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(inspector, textvariable=self.status_var, style="Panel.TLabel", wraplength=240).grid(row=8, column=0, sticky="ew", pady=(22, 0))

        output_panel = ttk.Frame(body, style="Panel.TFrame", padding=10)
        output_panel.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        output_panel.columnconfigure(0, weight=1)
        ttk.Label(output_panel, text="执行输出", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        output_frame = tk.Frame(output_panel, bg="#0b1220")
        output_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        output_frame.columnconfigure(0, weight=1)
        self.output_text = tk.Text(
            output_frame,
            height=10,
            bg="#0b1220",
            fg="#d1fae5",
            insertbackground="#d1fae5",
            relief="flat",
            font=("Cascadia Mono", 10),
            wrap="word",
        )
        self.output_text.grid(row=0, column=0, sticky="ew")
        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=scrollbar.set)
        self.output_text.tag_configure("error", foreground="#fca5a5")
        self.output_text.tag_configure("info", foreground="#93c5fd")
        self.output_text.tag_configure("success", foreground="#86efac")

    def _load_or_create_default_flow(self) -> None:
        if FLOW_PATH.is_file():
            try:
                self._set_flow(OperationFlow.load(FLOW_PATH))
                return
            except Exception as exc:
                messagebox.showwarning("加载失败", f"无法加载保存的流程: {exc}")

        self._set_flow(
            OperationFlow(
                nodes=[FlowNode(id="start", kind="start", label="Start", x=80, y=80)],
                edges=[],
            )
        )

    def _set_flow(self, flow: OperationFlow) -> None:
        self.nodes = {node.id: node for node in flow.nodes}
        self.edges = list(flow.edges)
        max_number = 0
        for node_id in self.nodes:
            if node_id.startswith("node-"):
                try:
                    max_number = max(max_number, int(node_id.removeprefix("node-")))
                except ValueError:
                    pass
        self.id_counter = itertools.count(max_number + 1)
        self.selected_node_id = None
        self.connect_source_id = None

    def add_command_node(self) -> None:
        node_id = self._next_node_id()
        self.nodes[node_id] = FlowNode(
            id=node_id,
            kind="command",
            label="Command",
            x=260,
            y=120 + len(self.nodes) * 34,
            text="echo hello",
        )
        self.select_node(node_id)
        self._redraw()

    def add_upload_node(self) -> None:
        node_id = self._next_node_id()
        self.nodes[node_id] = FlowNode(
            id=node_id,
            kind="upload",
            label="Upload",
            x=260,
            y=120 + len(self.nodes) * 34,
            local_path="D:\\build\\app.jar",
            remote_path="/home/project/app/app.jar",
        )
        self.select_node(node_id)
        self._redraw()

    def start_connect_mode(self) -> None:
        self.connect_source_id = None
        self.status_var.set("连接模式：先点击起点，再点击终点。")

    def delete_selected(self) -> None:
        if not self.selected_node_id or self.nodes[self.selected_node_id].kind == "start":
            return
        node_id = self.selected_node_id
        self.nodes.pop(node_id)
        self.edges = [edge for edge in self.edges if edge.source_id != node_id and edge.target_id != node_id]
        self.selected_node_id = None
        self._clear_inspector()
        self._redraw()

    def save_flow(self) -> None:
        OperationFlow(list(self.nodes.values()), self.edges).save(FLOW_PATH)
        self.status_var.set(f"已保存流程：{FLOW_PATH}")

    def load_flow_dialog(self) -> None:
        path = filedialog.askopenfilename(
            title="加载流程",
            filetypes=[("流程 JSON", "*.json"), ("所有文件", "*.*")],
            initialdir=str(FLOW_PATH.parent),
        )
        if not path:
            return
        try:
            self._set_flow(OperationFlow.load(Path(path)))
        except Exception as exc:
            messagebox.showerror("加载失败", str(exc))
            return
        self._redraw()
        self.status_var.set(f"已加载流程：{path}")

    def write_operations(self) -> None:
        try:
            text = OperationFlow(list(self.nodes.values()), self.edges).to_operations_text()
        except ValueError as exc:
            messagebox.showerror("流程无效", str(exc))
            return
        OPERATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        OPERATIONS_PATH.write_text(text, encoding="utf-8")
        self.save_flow()
        self.status_var.set(f"已写入：{OPERATIONS_PATH}")

    def run_operations(self) -> None:
        if self.is_running:
            return
        try:
            text = OperationFlow(list(self.nodes.values()), self.edges).to_operations_text()
        except ValueError as exc:
            messagebox.showerror("流程无效", str(exc))
            return
        OPERATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        OPERATIONS_PATH.write_text(text, encoding="utf-8")
        self.save_flow()
        self.output_text.delete("1.0", tk.END)
        self._append_output("开始执行流程...\n", "info")
        self.is_running = True
        self.run_state_var.set("运行中")
        thread = threading.Thread(target=self._run_worker, daemon=True)
        thread.start()

    def _run_worker(self) -> None:
        try:
            ssh_config = load_ssh_config(Path("config/ssh.json"))
            operations = load_operations(OPERATIONS_PATH)
            self._queue_output(f"Connecting to {ssh_config.username}@{ssh_config.host}:{ssh_config.port}\n", "info")
            with SshRemote(ssh_config, output=lambda text: self._queue_output(text + "\n", "normal")) as remote:
                runner = OperationRunner(remote, target_os=ssh_config.target_os, output=lambda text: self._queue_output(text + "\n", "info"))
                runner.run_all(operations)
            self._queue_output("All operations completed.\n", "success")
        except Exception as exc:
            self._queue_output(f"ERROR: {exc}\n", "error")
        finally:
            self.output_queue.put(("__done__", ""))

    def apply_selected_edits(self) -> None:
        if not self.selected_node_id:
            return
        node = self.nodes[self.selected_node_id]
        if node.kind == "command":
            command = self.command_var.get().strip()
            self.nodes[node.id] = FlowNode(
                id=node.id,
                kind=node.kind,
                label=_command_label(command),
                x=node.x,
                y=node.y,
                text=command,
            )
        elif node.kind == "upload":
            self.nodes[node.id] = FlowNode(
                id=node.id,
                kind=node.kind,
                label="Upload",
                x=node.x,
                y=node.y,
                local_path=self.local_path_var.get().strip(),
                remote_path=self.remote_path_var.get().strip(),
            )
        self._redraw()

    def on_canvas_press(self, event) -> None:  # type: ignore[no-untyped-def]
        node_id = self._node_at(event.x, event.y)
        if not node_id:
            self.selected_node_id = None
            self._clear_inspector()
            self._redraw()
            return

        if self.status_var.get().startswith("Connect mode"):
            self._handle_connect_click(node_id)
            return

        self.select_node(node_id)
        node = self.nodes[node_id]
        self.drag_node_id = node_id
        self.drag_offset = (event.x - node.x, event.y - node.y)

    def on_canvas_drag(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self.drag_node_id:
            return
        node = self.nodes[self.drag_node_id]
        self.nodes[node.id] = FlowNode(
            id=node.id,
            kind=node.kind,
            label=node.label,
            x=max(20, event.x - self.drag_offset[0]),
            y=max(20, event.y - self.drag_offset[1]),
            text=node.text,
            local_path=node.local_path,
            remote_path=node.remote_path,
        )
        self._redraw()

    def on_canvas_release(self, _event) -> None:  # type: ignore[no-untyped-def]
        self.drag_node_id = None

    def select_node(self, node_id: str) -> None:
        self.selected_node_id = node_id
        node = self.nodes[node_id]
        self.command_var.set(node.text if node.kind == "command" else "")
        self.local_path_var.set(node.local_path if node.kind == "upload" else "")
        self.remote_path_var.set(node.remote_path if node.kind == "upload" else "")
        self.status_var.set(f"Selected {node.label}")

    def _handle_connect_click(self, node_id: str) -> None:
        if self.connect_source_id is None:
            self.connect_source_id = node_id
            self.status_var.set("连接模式：点击终点节点。")
            return
        if self.connect_source_id == node_id:
            self.status_var.set("连接模式：终点必须是另一个节点。")
            return
        edge = FlowEdge(self.connect_source_id, node_id)
        reverse = FlowEdge(node_id, self.connect_source_id)
        if edge not in self.edges and reverse not in self.edges:
            self.edges.append(edge)
        self.connect_source_id = None
        self.status_var.set("已添加箭头。")
        self._redraw()

    def _redraw(self) -> None:
        self.canvas.delete("all")
        self.edge_items.clear()
        self.node_items.clear()
        for edge in self.edges:
            self._draw_edge(edge)
        for node in self.nodes.values():
            self._draw_node(node)

    def _draw_node(self, node: FlowNode) -> None:
        x1, y1 = node.x, node.y
        x2, y2 = x1 + NODE_WIDTH, y1 + NODE_HEIGHT
        fill = "#f8fafc"
        outline = "#38bdf8" if node.id == self.selected_node_id else "#64748b"
        if node.kind == "start":
            fill = "#dcfce7"
        elif node.kind == "upload":
            fill = "#fef3c7"
        rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=2)
        label = node.label
        detail = node.text if node.kind == "command" else node.remote_path
        text = self.canvas.create_text(
            x1 + 12,
            y1 + 12,
            anchor="nw",
            text=f"{label}\n{_shorten(detail)}",
            fill="#0f172a",
            width=NODE_WIDTH - 24,
        )
        self.node_items[node.id] = (rect, text)

    def _draw_edge(self, edge: FlowEdge) -> None:
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            return
        source = self.nodes[edge.source_id]
        target = self.nodes[edge.target_id]
        x1 = source.x + NODE_WIDTH
        y1 = source.y + NODE_HEIGHT // 2
        x2 = target.x
        y2 = target.y + NODE_HEIGHT // 2
        item = self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=2, fill="#7dd3fc", smooth=True)
        self.edge_items[(edge.source_id, edge.target_id)] = item

    def _node_at(self, x: int, y: int) -> str | None:
        for node_id, node in reversed(list(self.nodes.items())):
            if node.x <= x <= node.x + NODE_WIDTH and node.y <= y <= node.y + NODE_HEIGHT:
                return node_id
        return None

    def _clear_inspector(self) -> None:
        self.command_var.set("")
        self.local_path_var.set("")
        self.remote_path_var.set("")
        self.status_var.set("就绪")

    def _next_node_id(self) -> str:
        return f"node-{next(self.id_counter)}"

    def _queue_output(self, text: str, tag: str) -> None:
        self.output_queue.put((text, tag))

    def _drain_output_queue(self) -> None:
        while True:
            try:
                text, tag = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if text == "__done__":
                self.is_running = False
                self.run_state_var.set("未运行")
            else:
                self._append_output(text, tag)
        self.after(100, self._drain_output_queue)

    def _append_output(self, text: str, tag: str = "normal") -> None:
        self.output_text.insert(tk.END, text, tag)
        self.output_text.see(tk.END)


def _shorten(value: str, limit: int = 42) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _command_label(command: str) -> str:
    if not command:
        return "Command"
    return command.split()[0][:24]


def main() -> None:
    app = FlowEditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
