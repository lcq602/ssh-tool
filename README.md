# SSH Tool

这是一个 Windows 上使用的 SSH 操作执行工具。它读取连接配置和操作清单，连接远程服务器后按顺序执行命令，也支持上传文件。

## 文件位置

打包后的可执行文件位于：

```text
dist\ssh-tool.exe
```

运行 exe 时，配置文件放在 exe 同级目录：

```text
dist\config\ssh.json
dist\config\operations.txt
```

## 连接配置

复制示例配置并填写自己的服务器信息：

```powershell
copy config\ssh.example.json config\ssh.json
```

`config/ssh.json` 不会提交到 git。请不要把真实服务器地址、用户名或密码写进 README、示例文件或提交记录。

示例：

```json
{
  "host": "example.com",
  "port": 22,
  "username": "deploy",
  "password": "change-me",
  "target_os": "linux",
  "output_encoding": "auto",
  "timeout": 30
}
```

字段说明：

- `host`：服务器 IP 或域名。
- `port`：SSH 端口，通常是 `22`。
- `username`：SSH 用户名。
- `password`：SSH 密码。
- `target_os`：远程服务器系统，可填 `linux` 或 `windows`，默认 `linux`。
- `output_encoding`：远程命令输出编码。建议使用 `auto`；中文 Windows 服务器可显式填写 `gbk`。
- `timeout`：连接超时时间，单位秒。

## SSH 主机密钥

工具默认拒绝未知主机密钥。首次连接新服务器前，请先在本机信任该主机：

```powershell
ssh deploy@example.com
```

确认主机指纹后，OpenSSH 会把它写入当前用户的 `known_hosts`。之后再运行本工具即可连接。

## Linux 使用示例

`config/operations.txt`：

```text
cd /home/project/app
ls -la
./start.sh stop
./start.sh backup
upload D:\build\app.jar /home/project/app/app.jar
./start.sh start
```

## Windows 服务器使用示例

前提：远程 Windows 服务器已启用 OpenSSH Server，并允许该账号通过 SSH 登录。

`config/ssh.json` 示例：

```json
{
  "host": "192.0.2.10",
  "port": 22,
  "username": "Administrator",
  "password": "change-me",
  "target_os": "windows",
  "output_encoding": "gbk",
  "timeout": 30
}
```

中文 Windows 的 `dir`、`type` 等命令通常输出 GBK/CP936 编码，所以建议写：

```json
"output_encoding": "gbk"
```

`config/operations.txt` 示例：

```text
cd C:\deploy\app
dir
upload D:\build\app.jar C:\deploy\app\app.jar
start.bat stop
start.bat backup
start.bat start
```

## 操作配置规则

编辑 `config/operations.txt`：

```text
# 这是注释
cd /home/project/app
ls -la
upload D:\build\app.jar /home/project/app/app.jar
```

规则：

- 空行会跳过。
- `#` 开头的行会跳过。
- `upload 本地文件路径 远程文件路径` 表示上传文件。
- 如果本地路径包含空格，请加双引号，例如：`upload "D:\build output\app.jar" /tmp/app.jar`。
- 其他行都会当作远程命令执行。
- `cd` 会保持目录状态，后面的命令会在该目录下执行。
- 任一步失败都会停止执行。

## 日志和报错

每次运行都会在当前目录生成日志：

```text
logs\run-YYYYMMDD-HHMMSS.log
```

如果执行失败，控制台会显示：

```text
ERROR: 失败原因
Log written to: logs\run-YYYYMMDD-HHMMSS.log
```

日志文件会记录失败原因和 Python 堆栈，方便定位是连接失败、认证失败、文件不存在、上传失败，还是远程命令返回非 0。

## 开发运行

```powershell
uv run ssh-tool
```

也可以双击：

```text
run.bat
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 打包 exe

双击：

```text
build_exe.bat
```

或运行：

```powershell
.\build_exe.bat
```

打包完成后会生成：

```text
dist\ssh-tool.exe
dist\config\
```
