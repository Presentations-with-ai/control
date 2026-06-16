@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo PC Telegram Relay AGENT - Installer
echo Python 3.12 fixed version
echo ==========================================

echo Checking Python 3.12...
py -3.12 -V >nul 2>nul
if %errorlevel% neq 0 (
  echo Python 3.12 not found.
  echo Trying to install Python 3.12 with winget...
  winget install -e --id Python.Python.3.12 --scope user
  echo.
  echo After installation, checking Python 3.12 again...
  py -3.12 -V >nul 2>nul
  if %errorlevel% neq 0 (
    echo.
    echo Python 3.12 still not found.
    echo Install Python 3.12 manually, then run this file again:
    echo https://www.python.org/downloads/release/python-31210/
    start https://www.python.org/downloads/release/python-31210/
    pause
    exit /b 1
  )
)

if exist .venv\pyvenv.cfg (
  findstr /C:"version = 3.12" .venv\pyvenv.cfg >nul 2>nul
  if %errorlevel% neq 0 (
    echo Existing .venv is not Python 3.12. Removing old .venv...
    rmdir /s /q .venv
  )
)

if not exist .venv (
  echo Creating venv with Python 3.12...
  py -3.12 -m venv .venv
  if %errorlevel% neq 0 (
    echo Failed to create .venv with Python 3.12.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
python -V

python -m pip install --upgrade pip
if %errorlevel% neq 0 (
  echo Failed to upgrade pip.
  pause
  exit /b 1
)

pip install -r requirements.txt
if %errorlevel% neq 0 (
  echo.
  echo Failed to install requirements.
  echo Usually this happens if venv was created with wrong Python version.
  echo Delete .venv and run install_agent_windows.bat again.
  pause
  exit /b 1
)

if not exist .env (
  copy .env.example .env
  echo Created .env. Fill AGENT_BOT_TOKEN and PC_NAME now.
  notepad .env
)

call setup_autostart.bat

echo.
echo Done.
echo Agent will run hidden on Windows startup.
echo You can test with start_visible_agent.bat
pause
