@echo off
setlocal
cd /d "%~dp0"
if not exist "start.ps1" (
  echo [ERROR] start.ps1 not found in %CD%
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\start.ps1" %*
if errorlevel 1 (
  pause
  exit /b 1
)
endlocal
