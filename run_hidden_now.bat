@echo off
cd /d "%~dp0"
wscript "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\pc_telegram_relay.vbs"
echo Started hidden via autostart VBS.
pause
