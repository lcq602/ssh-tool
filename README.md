# SSH Tool

这是一个通用的 Windows SSH 操作执行器。它读取连接配置和操作配置，连接远程服务器后逐行执行命令，也支持上传文件。

## 文件位置

打包后的可执行文件在：

```text
dist\ssh-tool.exe
```

运行 exe 时，配置文件放在 exe 同级目录：

```text
dist\config\ssh.json
dist\config\operations.txt
```

## 连接配置

编辑 `config/ssh.json`：

```json
{
  "host": "140.143.235.93",
  "port": 22,
  "username": "root",
  "password": "lcqLCQ+521",
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
- `target_os`：远程服务器系统，可填 `linux` 或 `windows`，不写时默认 `linux`。
- `output_encoding`：远程命令输出编码。建议用 `auto`；中文 Windows 可显式填 `gbk`。
- `timeout`：连接超时时间，单位秒。

## Linux 使用示例

`config/ssh.json`：

```json
{
  "host": "140.143.235.93",
  "port": 22,
  "username": "root",
  "password": "lcqLCQ+521",
  "target_os": "linux",
  "output_encoding": "auto",
  "timeout": 30
}
```

`config/operations.txt`：

```text
cd /home/project/FundValuation
ls -la
./start.sh stop
./start.sh backup
upload D:\build\FundValuation.jar /home/project/FundValuation/FundValuation.jar
./start.sh start
```

## Windows 服务器使用示例

前提：远程 Windows 服务器已经开启 OpenSSH Server，并允许账号密码登录。

`config/ssh.json` 示例：

```json
{
  "host": "192.168.1.20",
  "port": 22,
  "username": "Administrator",
  "password": "YourPassword",
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
cd C:\deploy\FundValuation
dir
upload D:\build\FundValuation.jar C:\deploy\FundValuation\FundValuation.jar
start.bat stop
start.bat backup
start.bat start
```

也可以执行普通 Windows 命令：

```text
cd C:\deploy
dir
whoami
type app.log
```

## 操作配置规则

编辑 `config/operations.txt`：

```text
# 这是注释
cd /home/project/FundValuation
ls -la
upload D:\build\app.jar /home/project/FundValuation/app.jar
```

规则：

- 空行会跳过。
- `#` 开头的行会跳过。
- `upload 本地文件路径 远程文件路径` 表示上传文件。
- 如果本地路径包含空格，请加双引号，例如 `upload "D:\build output\app.jar" /tmp/app.jar`。
- 其他行都当作远程命令执行。
- `cd` 会保持目录状态，后面的命令会在该目录下执行。
- 任一步失败都会停止执行。

## 日志和报错原因

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
cd C:\Users\24920\Desktop\BigModelSetup\ssh-tool
uv run ssh-tool
```

也可以双击：

```text
run.bat
```

## 打包 exe

双击：

```text
build_exe.bat
```

或者运行：

```powershell
cd C:\Users\24920\Desktop\BigModelSetup\ssh-tool
.\build_exe.bat
```

打包完成后会生成：

```text
dist\ssh-tool.exe
dist\config\
```
