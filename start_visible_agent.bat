@echo off
cd /d "%~dp0"
if not exist .venv (
  echo .venv not found. Run install_agent_windows.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python agent_bot.pyw
pause
