# 迭代日志

## v2.1 — 2026-06-04

### 新增
- **中英文双语言支持**（`l10n.py`）
  - 自动检测 Windows 系统语言，中文显示中文界面，其他语言显示英文
  - 所有 UI 字符串集中管理，易于扩展更多语言
- **可视化步骤面板**
  - 用游戏化步骤列表替代纯文本日志（✅ 完成 / ⟳ 执行中/动画 / ⏳ 等待 / ❌ 失败）
  - 执行中的步骤图标每 500ms 旋转（⟳ → / → — → \）
  - 超过 8 步自动出现滚动条
  - 保留精简日志区显示命令输出
- **窗口高度调整**：380px → 480px 适配步骤面板

### 修改
- `src/ssh_tool/sl_gui.py` 全面重构：
  - 布局：标题栏 → 连接状态 → 步骤列表面板 → 日志区 → 进度条 → 状态提示
  - 所有硬编码字符串替换为 L10n 语言表
- `src/ssh_tool/main.py`：
  - GUI 模式自动检测语言并传入面板
  - worker 线程发送 `step_item` 消息驱动步骤面板状态

### 测试
- 新增 `tests/test_l10n.py`（10 个测试用例）
- 全部 40 个测试通过

---

## v2.0 — 2026-06-03

### 新增
- **Solo Leveling 风格浮动面板 GUI**（`sl_gui.py`）
  - 暗夜蓝黑主题 + 青蓝发光边框 + 金色标题
  - 面板居中显示，可拖动，置顶
  - 连接状态指示（青色圆点）、命令输出区（彩色标签）、发光进度条、成功/失败状态
- **GUI/CLI 双模式**（`main.py`）
  - 打包 exe 自动启动 GUI，`--cli` 参数切回传统控制台
  - 线程 + 队列安全传递消息
- **`--noconsole` 打包**（`build_exe.bat`）
  - `python -m PyInstaller` 替代 `uv run` 避免 trampoline 错误
  - exe 运行时无 cmd 黑框

### 修改
- `src/ssh_tool/main.py` — 新增 `_run_cli()` / `_run_gui()` 双模式
- `src/ssh_tool/config.py` — 新增 `auto_accept_key` 配置项
- `src/ssh_tool/remote.py` — 根据 `auto_accept_key` 切换 `AutoAddPolicy` / `RejectPolicy`
- `build_exe.bat` — 添加 `--noconsole`

### 测试
- 新增 `tests/test_sl_gui.py`（9 个 GuiOutput 消息队列测试）
- 全部 30 个测试通过

---

## v1.0 — 首次提交

### 功能
- SSH 远程连接和命令执行
- 配置文件驱动（ssh.json + operations.txt）
- 文件上传（upload 指令）
- 控制台输出（ConsoleOutput）
- 日志记录（文件日志）
- known_hosts 安全校验

### 技术栈
- Python 3.12+, paramiko, PyInstaller
- 测试：pytest（21 个测试用例）