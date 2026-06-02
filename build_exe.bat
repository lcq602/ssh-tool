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
  echo Build failed.
  pause
  exit /b 1
)

if exist dist\config rmdir /s /q dist\config
xcopy config dist\config\ /e /i /y >nul

echo.
echo Build complete: dist\ssh-tool.exe
echo Config copied to: dist\config
pause
