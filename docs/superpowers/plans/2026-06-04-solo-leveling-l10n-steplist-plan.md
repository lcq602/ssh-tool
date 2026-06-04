# 双语言 + 可视化步骤面板 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 添加中文/英文双语言支持 + 将日志区替换为游戏化的步骤任务列表

**Architecture:** 新增 `l10n.py` 语言模块 (L10n dataclass + 自动检测) + 重构 `sl_gui.py` 布局 (可滚动步骤面板 + 旋转动画 + 精简日志区) + `main.py` 发送 step_item 消息

**Tech Stack:** Python 3.12+, Tkinter, `locale` 标准库

---

### Task 1: 创建语言支持模块 `l10n.py`

**Files:**
- Create: `src/ssh_tool/l10n.py`
- Test: `tests/test_l10n.py`

**关键设计：**
- `L10n` frozen dataclass，所有 UI 字符串作为属性，英文为默认值
- `_ZH` dict 提供中文覆盖（添加新语言只需加 dict + 分支）
- `detect_language()` 使用 `locale.getlocale(locale.LC_CTYPE)` 检测系统语言
- `get_l10n(lang="auto")` 工厂函数

```python
_ZH: dict[str, str] = {
    "title": "⚜ 系统 ⚜",
    "initializing": "◆ 初始化中",
    "connecting": "◆ 连接中  ● {user}@{host}:{port} ({os})",
    "step_fmt": "──── 步骤 {n}/{total}  ({pct}%)  ────",
    "all_done": "✓ 所有操作已完成",
    "log_info": ">> {msg}",
    "log_cmd": "$ {msg}",
    "log_error": "日志: {path}",
    "step_pending": "⏳",
    "step_done": "✅",
    "step_error": "❌",
}
```

**测试用例：** detect_language 返回 `zh`/`en`、get_l10n("en") 返回英文、get_l10n("zh") 返回中文、格式化字符串正确

---

### Task 2: GuiOutput 新增 step_item 方法

**Files:**
- Modify: `src/ssh_tool/sl_gui.py`

在 `GuiOutput` 类新增：

```python
def step_item(self, index: int, text: str, status: str) -> None:
    self._queue.put(("step_item", index, text, status))
```

status 取值：`"pending"` | `"running"` | `"done"` | `"error"`

---

### Task 3: 重构 SoloLevelingGUI 布局 — 步骤面板

**Files:**
- Modify: `src/ssh_tool/sl_gui.py`

**布局变化：**
```
旧布局：title → conn → sep_label → log_text(11行) → progress → status
新布局：title → conn → step_list(滚动, ~8行) → log_text(4行) → progress → status
```

**__init__ 变更：**
- 接受 `l10n: L10n | None = None` 参数
- 新增实例变量：`_steps: list[dict]`、`_step_rotation_index`、`_running_step_index`
- 窗口高度 380 → 480

**_create_widgets 变更：**
- 删除 `sep_frame` 和 `_sep_label`
- 新增 `_step_container` → `_step_canvas`(可滚动) → `_step_inner`(行容器)
- `_log_text` height 11 → 4, `expand=True` → 移除 expand
- 保留 progress 和 status 不变

**新增方法：**
- `_rebuild_step_list()` — 根据 `_steps` 数据重建所有行
- `_step_icon_and_color(status)` — 返回 (图标, 颜色) 元组
- `_animate_step_icons()` — 每 500ms 旋转 running 步骤图标 (⟳ / — \)
- `_on_step_item(index, text, status)` — 处理 step_item 消息

---

### Task 4: 应用语言字符串到所有 UI 文字

**Files:**
- Modify: `src/ssh_tool/sl_gui.py`

| 位置 | 旧值 | 新值 |
|------|------|------|
| 标题 label | `"⚜  SYSTEM  ⚜"` | `self._l10n.title` |
| 连接状态 label | `"◆  INITIALIZING"` | `self._l10n.initializing` |
| _on_connection | f"◆ CONNECTING ● ..." | `self._l10n.connecting.format(...)` |
| _on_info | f">> {message}" | `self._l10n.log_info.format(msg=message)` |
| _on_line | f"$ {message}" | `self._l10n.log_cmd.format(msg=message)` |
| _on_error 日志行 | f"LOG: {path}" | `self._l10n.log_error.format(path=path)` |
| _on_success 状态 | `"✓ All operations completed."` | `self._l10n.all_done` |
| _on_error 状态 | f"✗ {message}" | `self._l10n.error_prefix.format(msg=message)` |

---

### Task 5: main.py 接入语言检测 + 发送 step_item

**Files:**
- Modify: `src/ssh_tool/main.py`

**worker() 函数修改：**
- 加载 operations 后遍历，对每个 op 发送 `gui_output.step_item(i, text, "pending")`
- 标记第一个为 `"running"`
- 每次执行完一个 op 后标记下一个为 `"running"`
- 最后标记最后一个为 `"done"`

**_run_gui 函数修改：**
- `from ssh_tool.l10n import get_l10n` (放入函数内部避免顶层引入)
- `l10n = get_l10n()` → `SoloLevelingGUI(msg_queue, l10n=l10n)`
- `gui_output.header(l10n.title)`、`gui_output.success(l10n.all_done)`

---

### Task 6: 更新测试

**Files:**
- Modify: `tests/test_sl_gui.py` — 新增 step_item 消息队列测试
- Create: `tests/test_l10n.py` — 语言检测和格式化测试

```
# test_sl_gui.py 新增：
def test_step_item_queues_message()  → verify ("step_item", 0, "ls", "pending")
def test_step_item_status_values()   → verify all 4 statuses

# test_l10n.py 创建：
def test_detect_language_return_string()
def test_get_l10n_en_returns_english()
def test_get_l10n_zh_returns_chinese()
def test_l10n_formatting()
```

---

### Task 7: 打包验证

```bash
.venv\Scripts\python.exe -m PyInstaller --clean --onefile --noconsole --paths src --name ssh-tool src/ssh_tool/main.py
```

双击 `dist/ssh-tool.exe` 验证：
- 中文系统自动显示中文界面
- 步骤面板显示每个操作的状态图标
- 执行中的步骤图标旋转动画
- 日志区显示当前命令输出

### 自检清单

- [ ] L10n dataclass 覆盖所有 UI 字符串
- [ ] 中文检测在 Windows 中文环境下工作
- [ ] step_list 可滚动处理 >8 步的情况
- [ ] 动画耗时不影响主流程 (after 回调非阻塞)
- [ ] 语言切换不改变功能逻辑
- [ ] 窗口高度适应新布局 (480px)
- [ ] 所有测试通过