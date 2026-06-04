@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\start.ps1" %*
if errorlevel 1 (
  pause
  exit /b 1
)
endlocal
