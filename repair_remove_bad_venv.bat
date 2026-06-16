@echo off
cd /d "%~dp0"
if exist .venv (
  echo Removing old .venv...
  rmdir /s /q .venv
)
echo Done. Now run installer again.
pause
