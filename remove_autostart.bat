@echo off
set VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\pc_telegram_relay.vbs
if exist "%VBS%" (
  del "%VBS%"
  echo Removed: %VBS%
) else (
  echo Autostart file not found.
)
pause
