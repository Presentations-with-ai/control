@echo off
setlocal
cd /d "%~dp0"

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS=%STARTUP%\pc_telegram_relay.vbs
set LAUNCHER=%~dp0launcher.pyw
set PYTHONW=%~dp0.venv\Scripts\pythonw.exe

if not exist "%PYTHONW%" (
  echo pythonw.exe not found in .venv. Run install_windows.bat first.
  pause
  exit /b 1
)

(
echo Set WshShell = CreateObject("WScript.Shell"^)
echo WshShell.Run """" ^& "%PYTHONW%" ^& """ """ ^& "%LAUNCHER%" ^& """", 0, False
) > "%VBS%"

echo Autostart created:
echo %VBS%
