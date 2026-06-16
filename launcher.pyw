import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
target = BASE_DIR / "agent_bot.pyw"

pythonw = Path(sys.executable)
if pythonw.name.lower() == "python.exe":
    candidate = pythonw.with_name("pythonw.exe")
    if candidate.exists():
        pythonw = candidate

subprocess.Popen([str(pythonw), str(target)], cwd=str(BASE_DIR), shell=False)
