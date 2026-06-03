@echo off
setlocal
cd /d "%~dp0"

uv run pyinstaller ^
  --clean ^
  --onefile ^
  --paths src ^
  --name ssh-tool ^
  src\ssh_tool\main.py

if errorlevel 1 (
  echo CLI build failed.
  pause
  exit /b 1
)

uv run pyinstaller ^
  --clean ^
  --onefile ^
  --windowed ^
  --paths src ^
  --name ssh-tool-gui ^
  src\ssh_tool\flow_gui.py

if errorlevel 1 (
  echo GUI build failed.
  pause
  exit /b 1
)

if exist dist\config rmdir /s /q dist\config
mkdir dist\config
copy config\ssh.example.json dist\config\ssh.example.json >nul
copy config\operations.txt dist\config\operations.txt >nul

echo.
echo Build complete: dist\ssh-tool.exe
echo GUI complete: dist\ssh-tool-gui.exe
echo Config copied to: dist\config
pause
