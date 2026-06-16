import asyncio
import base64
import ctypes
import os
import platform
import shutil
import socket
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import mss
import mss.tools
import psutil
import pyautogui
import pyperclip
from PIL import Image, ImageDraw, ImageFont

try:
    from send2trash import send2trash
except Exception:
    send2trash = None


BASE_DIR = Path(__file__).resolve().parent
BOT_TRASH_DIR = BASE_DIR / "_bot_trash"

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

APP_WHITELIST = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "notepad": "notepad.exe",
    "calc": "calc.exe",
    "telegram": str(Path.home() / r"AppData\Roaming\Telegram Desktop\Telegram.exe"),
    "explorer": "explorer.exe",
    "taskmgr": "taskmgr.exe",
    "settings": "ms-settings:",
    "control": "control.exe",
}

PROTECTED_PROCESS_NAMES = {
    "msmpeng.exe",
    "securityhealthservice.exe",
    "nissrv.exe",
    "windefend.exe",
}

VALID_KEYS = set(list("abcdefghijklmnopqrstuvwxyz") + list("0123456789") + [
    "enter", "return", "esc", "escape", "tab", "space", "backspace", "delete",
    "del", "insert", "home", "end", "pageup", "pagedown", "pgup", "pgdn",
    "up", "down", "left", "right",
    "ctrl", "control", "shift", "alt", "win", "command", "option",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "capslock", "numlock", "scrolllock", "printscreen", "prtsc", "pause",
    "volumeup", "volumedown", "volumemute",
])

KEY_ALIASES = {
    "escape": "esc",
    "control": "ctrl",
    "return": "enter",
    "del": "delete",
    "pgup": "pageup",
    "pgdn": "pagedown",
    "prtsc": "printscreen",
}


COMMAND_DESCRIPTIONS = {
    "help": "список команд",
    "screen": "скриншот",
    "off": "выключить ПК",
    "restart": "перезагрузить ПК",
    "open_url": "открыть сайт",
    "open_app": "открыть приложение",
    "run_file": "запустить файл по пути через PowerShell",
    "beep": "короткий звук",
    "boot_time": "когда включён ПК",
    "chrome": "открыть Chrome",
    "close_app": "закрыть программу",
    "minimize_all": "свернуть все окна",
    "copy_file": "копировать файл",
    "create_folder": "создать папку",
    "list": "список папки",
    "search_chrome": "поиск в Chrome",
    "ip": "IP",
    "lock": "заблокировать экран",
    "message": "сообщение на экране",
    "move_file": "переместить файл",
    "mute": "mute",
    "volup": "звук громче",
    "voldown": "звук тише",
    "network_info": "информация о сети",
    "rename_file": "переименовать",
    "send_file": "отправить файл с ПК в Telegram",
    "save_file": "сохранить файл из Telegram на ПК",
    "delete_file": "удалить файл по пути в корзину",
    "mouse_pos": "позиция мыши",
    "mouse_move": "переместить мышь",
    "mouse_click": "левый клик",
    "mouse_right": "правый клик",
    "mouse_double": "двойной клик",
    "mouse_scroll": "скролл",
    "grid": "скрин с сеткой",
    "move_cell": "курсор в клетку",
    "click_cell": "клик по клетке",
    "double_cell": "двойной клик по клетке",
    "fine": "увеличить область",
    "click_fine": "точный клик по цепочке",
    "move_fine": "точно переместить курсор",
    "double_fine": "точный двойной клик",
    "click_here": "клик здесь",
    "double_here": "двойной клик здесь",
    "left": "курсор влево",
    "right": "курсор вправо",
    "up": "курсор вверх",
    "down": "курсор вниз",
    "type": "вставить текст",
    "type_enter": "вставить текст и Enter",
    "enter": "Enter",
    "backspace": "Backspace",
    "ctrl_a": "Ctrl+A",
    "key": "нажать клавишу",
    "hotkey": "комбинация клавиш",
    "key_down": "зажать клавишу",
    "key_up": "отпустить клавишу",
    "esc": "Esc",
    "tab": "Tab",
    "space": "Space",
    "alt_tab": "Alt+Tab",
    "ctrl_c": "Ctrl+C",
    "ctrl_v": "Ctrl+V",
    "ctrl_x": "Ctrl+X",
    "ctrl_z": "Ctrl+Z",
    "ctrl_s": "Ctrl+S",
    "ctrl_f": "Ctrl+F",
    "ctrl_l": "Ctrl+L",
    "f5": "F5",
}


def split_command_line(text: str):
    text = (text or "").strip()
    if text.startswith("/"):
        text = text[1:]
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower() if parts else ""
    args = parts[1].strip() if len(parts) > 1 else ""
    return cmd, args


def normalize_path(path_text: str) -> Path:
    path_text = path_text.strip().strip('"').strip("'")
    if not path_text:
        raise ValueError("Путь пустой.")
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    else:
        path = path.resolve()
    return path


def parse_two_paths(args: str):
    if "|" not in args:
        raise ValueError("Нужно использовать разделитель | между путями.")
    left, right = args.split("|", 1)
    return normalize_path(left), normalize_path(right)


def format_size(num: int) -> str:
    try:
        num = float(num)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if num < 1024:
                return f"{num:.1f} {unit}"
            num /= 1024
        return f"{num:.1f} PB"
    except Exception:
        return str(num)


def get_chrome_exe() -> str:
    for p in CHROME_PATHS:
        if Path(p).exists():
            return p
    return "chrome"


def open_in_chrome(url: str):
    chrome = get_chrome_exe()
    if Path(chrome).exists():
        subprocess.Popen([chrome, url], shell=False)
    else:
        subprocess.Popen(["cmd", "/c", "start", "chrome", url], shell=False)


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_ = s.getsockname()[0]
        s.close()
        return ip_
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception as e:
            return f"Ошибка: {e}"


def safe_process_name(name: str) -> str:
    name = name.strip().strip('"').strip("'").lower()
    if not name:
        raise ValueError("Имя процесса пустое.")
    if not name.endswith(".exe"):
        name += ".exe"
    if name in PROTECTED_PROCESS_NAMES:
        raise ValueError("Этот системный процесс не будет закрыт.")
    return name


def file_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def b64_to_file(data_b64: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(data_b64.encode("ascii")))


def make_text(text: str):
    return {"kind": "text", "text": str(text)}


def make_photo(path: Path, caption: str = ""):
    return {
        "kind": "photo",
        "filename": path.name,
        "caption": caption,
        "data_b64": file_to_b64(path),
    }


def make_file(path: Path, caption: str = ""):
    return {
        "kind": "file",
        "filename": path.name,
        "caption": caption,
        "data_b64": file_to_b64(path),
    }


def take_screenshot() -> Path:
    screenshot_path = Path(tempfile.gettempdir()) / "pc_screen.png"
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
        mss.tools.to_png(img.rgb, img.size, output=str(screenshot_path))
    return screenshot_path


def take_grid_screenshot(cols: int = 10, rows: int = 6) -> Path:
    screenshot_path = Path(tempfile.gettempdir()) / "pc_screen_grid.png"
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
        image = Image.frombytes("RGB", img.size, img.rgb)
        draw = ImageDraw.Draw(image)

        width, height = image.size
        cell_w = width / cols
        cell_h = height / rows

        try:
            font_big = ImageFont.truetype("arial.ttf", max(20, width // 55))
            font_small = ImageFont.truetype("arial.ttf", max(14, width // 90))
        except Exception:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()

        for c in range(cols + 1):
            x = int(c * cell_w)
            draw.line([(x, 0), (x, height)], fill=(255, 0, 0), width=3)

        for r in range(rows + 1):
            y = int(r * cell_h)
            draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=3)

        for r in range(rows):
            for c in range(cols):
                label = f"{chr(65 + c)}{r + 1}"
                x = int(c * cell_w + 12)
                y = int(r * cell_h + 10)
                try:
                    bbox = draw.textbbox((x, y), label, font=font_big)
                    draw.rectangle([bbox[0]-6, bbox[1]-4, bbox[2]+6, bbox[3]+4], fill=(0, 0, 0))
                except Exception:
                    draw.rectangle([x - 6, y - 4, x + 55, y + 28], fill=(0, 0, 0))
                draw.text((x, y), label, fill=(255, 255, 255), font=font_big)

        header = "Пиши: /fine C4 или /click_cell C4"
        draw.rectangle([10, height - 45, min(width - 10, 620), height - 10], fill=(0, 0, 0))
        draw.text((20, height - 38), header, fill=(255, 255, 255), font=font_small)
        image.save(screenshot_path)

    return screenshot_path


def parse_cell(cell: str, cols: int, rows: int):
    cell = cell.strip().upper()
    if len(cell) < 2:
        raise ValueError("Формат клетки должен быть типа A1, C4, D3.")
    letter = cell[0]
    number_text = cell[1:]
    if not letter.isalpha() or not number_text.isdigit():
        raise ValueError("Формат клетки должен быть типа A1, C4, D3.")
    col = ord(letter) - ord("A")
    row = int(number_text) - 1
    if col < 0 or col >= cols or row < 0 or row >= rows:
        raise ValueError(f"Клетка {cell} вне сетки. Разрешено A1-{chr(65 + cols - 1)}{rows}.")
    return col, row


def parse_cells_path(args: str):
    cells = [x.strip().upper() for x in args.split() if x.strip()]
    if not cells:
        raise ValueError("Нужно указать хотя бы одну клетку. Пример: /fine A1 или /fine A1 D3")
    return cells


def refine_bounds_by_cells(cells):
    screen_w, screen_h = pyautogui.size()
    left = 0.0
    top = 0.0
    right = float(screen_w)
    bottom = float(screen_h)

    for i, cell in enumerate(cells):
        if i == 0:
            cols, rows = 10, 6
        else:
            cols, rows = 5, 5

        col, row = parse_cell(cell, cols, rows)
        width = right - left
        height = bottom - top
        cell_w = width / cols
        cell_h = height / rows
        new_left = left + col * cell_w
        new_top = top + row * cell_h
        new_right = new_left + cell_w
        new_bottom = new_top + cell_h
        left, top, right, bottom = new_left, new_top, new_right, new_bottom

    return left, top, right, bottom


def cells_path_to_center(cells):
    left, top, right, bottom = refine_bounds_by_cells(cells)
    return int((left + right) / 2), int((top + bottom) / 2)


def cell_to_xy(cell: str, cols: int = 10, rows: int = 6):
    col, row = parse_cell(cell, cols, rows)
    screen_w, screen_h = pyautogui.size()
    cell_w = screen_w / cols
    cell_h = screen_h / rows
    return int(col * cell_w + cell_w / 2), int(row * cell_h + cell_h / 2)


def take_recursive_fine_screenshot(cells, fine_cols: int = 5, fine_rows: int = 5) -> Path:
    output_path = Path(tempfile.gettempdir()) / "pc_screen_recursive_fine_grid.png"
    left, top, right, bottom = refine_bounds_by_cells(cells)

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
        image = Image.frombytes("RGB", img.size, img.rgb)
        crop = image.crop((int(left), int(top), int(right), int(bottom)))

        zoom_w = 1000
        ratio = zoom_w / max(1, crop.size[0])
        zoom_h = max(300, int(crop.size[1] * ratio))
        crop = crop.resize((zoom_w, zoom_h))

        draw = ImageDraw.Draw(crop)
        width, height = crop.size
        cell_w = width / fine_cols
        cell_h = height / fine_rows

        try:
            font_big = ImageFont.truetype("arial.ttf", max(24, width // 38))
            font_small = ImageFont.truetype("arial.ttf", max(15, width // 75))
        except Exception:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()

        for c in range(fine_cols + 1):
            x = int(c * cell_w)
            draw.line([(x, 0), (x, height)], fill=(255, 0, 0), width=4)

        for r in range(fine_rows + 1):
            y = int(r * cell_h)
            draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=4)

        for r in range(fine_rows):
            for c in range(fine_cols):
                label = f"{chr(65 + c)}{r + 1}"
                x = int(c * cell_w + 12)
                y = int(r * cell_h + 10)
                try:
                    bbox = draw.textbbox((x, y), label, font=font_big)
                    draw.rectangle([bbox[0]-6, bbox[1]-4, bbox[2]+6, bbox[3]+4], fill=(0, 0, 0))
                except Exception:
                    draw.rectangle([x - 6, y - 4, x + 60, y + 32], fill=(0, 0, 0))
                draw.text((x, y), label, fill=(255, 255, 255), font=font_big)

        path_text = " ".join(cells)
        header = f"Область: {path_text} | дальше: /fine {path_text} C3"
        footer = f"Клик: /click_fine {path_text} C3"
        draw.rectangle([10, height - 82, min(width - 10, 980), height - 10], fill=(0, 0, 0))
        draw.text((20, height - 74), header, fill=(255, 255, 255), font=font_small)
        draw.text((20, height - 42), footer, fill=(255, 255, 255), font=font_small)
        crop.save(output_path)

    return output_path


def nudge_mouse(dx: int = 0, dy: int = 0):
    x, y = pyautogui.position()
    screen_w, screen_h = pyautogui.size()
    nx = max(0, min(screen_w - 1, x + dx))
    ny = max(0, min(screen_h - 1, y + dy))
    pyautogui.moveTo(nx, ny, duration=0.05)
    return nx, ny


def normalize_key_name(key: str) -> str:
    key = key.strip().lower()
    if not key:
        raise ValueError("Клавиша не указана.")
    key = KEY_ALIASES.get(key, key)
    if key not in VALID_KEYS:
        raise ValueError(f"Клавиша '{key}' не разрешена. Примеры: f, enter, esc, tab, ctrl, f5.")
    return key


def parse_hotkey_args(args: str):
    args = args.strip().lower().replace("+", " ")
    if not args:
        raise ValueError("Комбинация не указана.")
    keys = [normalize_key_name(x) for x in args.split() if x.strip()]
    if len(keys) < 2:
        raise ValueError("Для комбинации нужно минимум 2 клавиши. Пример: /hotkey ctrl c")
    if len(keys) > 5:
        raise ValueError("Слишком длинная комбинация. Максимум 5 клавиш.")
    return keys


def execute_local_command(pc_name: str, command_line: str, file_payload=None):
    pyautogui.FAILSAFE = False
    cmd, args = split_command_line(command_line)

    try:
        if cmd in {"", "help"}:
            lines = [f"📌 Команды ПК {pc_name}:"]
            for k, v in COMMAND_DESCRIPTIONS.items():
                lines.append(f"/{k} — {v}")
            return make_text("\n".join(lines))

        if cmd == "screen":
            return make_photo(take_screenshot(), f"🖥 Скриншот: {pc_name}")

        if cmd == "off":
            subprocess.run(["shutdown", "/s", "/t", "3"], shell=False)
            return make_text(f"🔴 Выключаю ПК {pc_name} через 3 секунды...")

        if cmd == "restart":
            subprocess.run(["shutdown", "/r", "/t", "3"], shell=False)
            return make_text(f"🔁 Перезагружаю ПК {pc_name} через 3 секунды...")

        if cmd == "open_url":
            url = args.strip()
            if not url:
                return make_text("Пример: /open_url https://google.com")
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                url = "https://" + url
            open_in_chrome(url)
            return make_text(f"✅ Открыл через Chrome на {pc_name}:\n{url}")

        if cmd == "open_app":
            app_name = args.strip().lower()
            if not app_name:
                return make_text("Пример: /open_app notepad\nДоступно: " + ", ".join(APP_WHITELIST.keys()))
            if app_name not in APP_WHITELIST:
                return make_text("⛔ Такого приложения нет в списке. Для запуска по пути используй /run_file.")
            target = APP_WHITELIST[app_name]
            if target == "ms-settings:":
                subprocess.Popen(["cmd", "/c", "start", "ms-settings:"], shell=False)
            else:
                subprocess.Popen(target, shell=True)
            return make_text(f"✅ Открыл приложение на {pc_name}: {app_name}")

        if cmd == "run_file":
            if not args:
                return make_text('Пример: /run_file "C:\\Users\\USER\\Desktop\\program.exe"')
            path = normalize_path(args)
            if not path.exists():
                return make_text("Файл не найден.")
            subprocess.Popen([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", f"Start-Process -FilePath \"{str(path)}\""
            ], shell=False)
            return make_text(f"✅ Запустил через PowerShell на {pc_name}:\n{path}")

        if cmd == "beep":
            import winsound
            winsound.Beep(1000, 500)
            return make_text(f"🔔 Beep на {pc_name}.")

        if cmd == "boot_time":
            boot = datetime.fromtimestamp(psutil.boot_time()).strftime("%d.%m.%Y %H:%M:%S")
            seconds = int(time.time() - psutil.boot_time())
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return make_text(f"⏱ {pc_name} включён:\n{boot}\nРаботает: {hours} ч {minutes} мин")

        if cmd == "chrome":
            chrome = get_chrome_exe()
            if Path(chrome).exists():
                subprocess.Popen([chrome], shell=False)
            else:
                subprocess.Popen(["cmd", "/c", "start", "chrome"], shell=False)
            return make_text(f"✅ Открыл Chrome на {pc_name}.")

        if cmd == "close_app":
            if not args:
                return make_text("Пример: /close_app chrome.exe")
            name = safe_process_name(args)
            closed = 0
            for p in psutil.process_iter(["pid", "name"]):
                try:
                    if p.info["name"] and p.info["name"].lower() == name:
                        p.kill()
                        closed += 1
                except Exception:
                    pass
            return make_text(f"✅ На {pc_name} закрыто процессов: {closed}")

        if cmd == "minimize_all":
            pyautogui.hotkey("win", "m")
            return make_text(f"✅ Все окна свёрнуты на {pc_name}.")

        if cmd == "copy_file":
            if not args:
                return make_text('Пример: /copy_file "C:\\old.txt" | "C:\\new.txt"')
            src, dst = parse_two_paths(args)
            if not src.exists() or not src.is_file():
                return make_text("Файл-источник не найден.")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return make_text(f"✅ Файл скопирован на {pc_name}:\n{dst}")

        if cmd == "create_folder":
            if not args:
                return make_text('Пример: /create_folder "C:\\Users\\USER\\Desktop\\NewFolder"')
            path = normalize_path(args)
            path.mkdir(parents=True, exist_ok=True)
            return make_text(f"✅ Папка создана на {pc_name}:\n{path}")

        if cmd == "list":
            if not args:
                return make_text('Пример: /list "C:\\Users\\USER\\Desktop"')
            folder = normalize_path(args)
            if not folder.exists():
                return make_text("Папка не найдена.")
            if not folder.is_dir():
                return make_text("Это не папка.")
            items = list(folder.iterdir())[:120]
            if not items:
                return make_text("Папка пустая.")
            lines = [f"📂 {pc_name}: {folder}\n"]
            for item in items:
                icon = "📁" if item.is_dir() else "📄"
                size = ""
                if item.is_file():
                    try:
                        size = f" — {format_size(item.stat().st_size)}"
                    except Exception:
                        pass
                lines.append(f"{icon} {item.name}{size}")
            return make_text("\n".join(lines))

        if cmd == "search_chrome":
            query = args.strip()
            if not query:
                return make_text("Пример: /search_chrome курс доллара")
            url = "https://www.google.com/search?q=" + quote_plus(query)
            open_in_chrome(url)
            return make_text(f"✅ Открыл поиск в Chrome на {pc_name}:\n{query}")

        if cmd == "ip":
            return make_text(f"🌐 {pc_name}\nLocal IP: {get_local_ip()}\nHostname: {socket.gethostname()}")

        if cmd == "lock":
            ctypes.windll.user32.LockWorkStation()
            return make_text(f"🔒 Блокирую экран на {pc_name}...")

        if cmd == "message":
            text = args.strip()
            if not text:
                return make_text("Пример: /message Привет")
            ctypes.windll.user32.MessageBoxW(0, text, f"Telegram PC Bot — {pc_name}", 0)
            return make_text(f"✅ Сообщение показано на {pc_name}.")

        if cmd == "move_file":
            if not args:
                return make_text('Пример: /move_file "C:\\old.txt" | "C:\\folder\\new.txt"')
            src, dst = parse_two_paths(args)
            if not src.exists():
                return make_text("Источник не найден.")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return make_text(f"✅ Перемещено на {pc_name}:\n{dst}")

        if cmd == "mute":
            pyautogui.press("volumemute")
            return make_text(f"🔇 Переключил mute на {pc_name}.")

        if cmd == "volup":
            count = int(args.strip()) if args.strip().isdigit() else 5
            count = max(1, min(count, 50))
            pyautogui.press("volumeup", presses=count)
            return make_text(f"🔊 На {pc_name} громкость увеличена на {count} шагов.")

        if cmd == "voldown":
            count = int(args.strip()) if args.strip().isdigit() else 5
            count = max(1, min(count, 50))
            pyautogui.press("volumedown", presses=count)
            return make_text(f"🔉 На {pc_name} громкость уменьшена на {count} шагов.")

        if cmd == "network_info":
            result = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace", shell=False)
            text = result.stdout or result.stderr
            return make_text(f"🌐 Network info {pc_name}:\n\n" + text[-3500:])

        if cmd == "rename_file":
            if not args:
                return make_text('Пример: /rename_file "C:\\old.txt" | "C:\\newname.txt"')
            old, new = parse_two_paths(args)
            if not old.exists():
                return make_text("Исходный файл/папка не найден.")
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
            return make_text(f"✅ Переименовано на {pc_name}:\n{new}")

        if cmd == "send_file":
            if not args:
                return make_text('Пример: /send_file "C:\\Users\\USER\\Desktop\\file.txt"')
            path = normalize_path(args)
            if not path.exists() or not path.is_file():
                return make_text("Файл не найден.")
            if path.stat().st_size > 45 * 1024 * 1024:
                return make_text("Файл слишком большой для Telegram.")
            return make_file(path, f"📄 {pc_name}")

        if cmd == "save_file":
            if not args:
                return make_text('Пример: отправь файл с caption /save_file "C:\\Users\\USER\\Desktop\\file.ext"')
            if not file_payload:
                return make_text("Файл не передан. Отправь документ с подписью /save_file путь.")
            dst = normalize_path(args)
            b64_to_file(file_payload["data_b64"], dst)
            return make_text(f"✅ Файл сохранён на {pc_name}:\n{dst}\nРазмер: {format_size(dst.stat().st_size)}")

        if cmd == "delete_file":
            if not args:
                return make_text('Пример: /delete_file "C:\\Users\\USER\\Desktop\\file.txt"')
            path = normalize_path(args)
            if not path.exists():
                return make_text("Файл не найден.")
            if path.is_dir():
                return make_text("Это папка. Команда удаляет только файлы.")
            if send2trash:
                send2trash(str(path))
                return make_text(f"🗑 Файл отправлен в корзину на {pc_name}:\n{path}")
            BOT_TRASH_DIR.mkdir(exist_ok=True)
            dst = BOT_TRASH_DIR / f"{int(time.time())}_{path.name}"
            shutil.move(str(path), str(dst))
            return make_text(f"🗑 send2trash недоступен. Файл перемещён в:\n{dst}")

        if cmd == "mouse_pos":
            x, y = pyautogui.position()
            return make_text(f"🖱 {pc_name}: x={x}, y={y}")

        if cmd == "mouse_move":
            parts = args.split()
            if len(parts) != 2:
                return make_text("Пример: /mouse_move 500 300")
            x, y = int(parts[0]), int(parts[1])
            pyautogui.moveTo(x, y, duration=0.2)
            return make_text(f"✅ {pc_name}: курсор x={x}, y={y}")

        if cmd == "mouse_click":
            pyautogui.click()
            return make_text(f"✅ Левый клик на {pc_name}.")

        if cmd == "mouse_right":
            pyautogui.click(button="right")
            return make_text(f"✅ Правый клик на {pc_name}.")

        if cmd == "mouse_double":
            pyautogui.doubleClick()
            return make_text(f"✅ Двойной клик на {pc_name}.")

        if cmd == "mouse_scroll":
            amount = int(args.strip()) if args.strip() else -5
            amount = max(-50, min(50, amount))
            pyautogui.scroll(amount)
            return make_text(f"✅ Прокрутка на {pc_name}: {amount}")

        if cmd == "grid":
            return make_photo(take_grid_screenshot(), f"🧭 Сетка экрана {pc_name}: A1-J6")

        if cmd == "move_cell":
            if not args:
                return make_text("Пример: /move_cell C4")
            x, y = cell_to_xy(args)
            pyautogui.moveTo(x, y, duration=0.2)
            return make_text(f"✅ {pc_name}: курсор в {args.upper()} → x={x}, y={y}")

        if cmd == "click_cell":
            if not args:
                return make_text("Пример: /click_cell C4")
            x, y = cell_to_xy(args)
            pyautogui.moveTo(x, y, duration=0.2)
            pyautogui.click()
            return make_text(f"✅ {pc_name}: клик в {args.upper()} → x={x}, y={y}")

        if cmd == "double_cell":
            if not args:
                return make_text("Пример: /double_cell C4")
            x, y = cell_to_xy(args)
            pyautogui.moveTo(x, y, duration=0.2)
            pyautogui.doubleClick()
            return make_text(f"✅ {pc_name}: двойной клик в {args.upper()} → x={x}, y={y}")

        if cmd == "fine":
            cells = parse_cells_path(args)
            return make_photo(take_recursive_fine_screenshot(cells), f"🔍 {pc_name}: область {' '.join(cells)}")

        if cmd == "click_fine":
            cells = parse_cells_path(args)
            x, y = cells_path_to_center(cells)
            pyautogui.moveTo(x, y, duration=0.15)
            pyautogui.click()
            return make_text(f"✅ {pc_name}: точный клик {' '.join(cells)} → x={x}, y={y}")

        if cmd == "move_fine":
            cells = parse_cells_path(args)
            x, y = cells_path_to_center(cells)
            pyautogui.moveTo(x, y, duration=0.15)
            return make_text(f"✅ {pc_name}: курсор {' '.join(cells)} → x={x}, y={y}")

        if cmd == "double_fine":
            cells = parse_cells_path(args)
            x, y = cells_path_to_center(cells)
            pyautogui.moveTo(x, y, duration=0.15)
            pyautogui.doubleClick()
            return make_text(f"✅ {pc_name}: двойной клик {' '.join(cells)} → x={x}, y={y}")

        if cmd == "click_here":
            pyautogui.click()
            x, y = pyautogui.position()
            return make_text(f"✅ {pc_name}: клик здесь x={x}, y={y}")

        if cmd == "double_here":
            pyautogui.doubleClick()
            x, y = pyautogui.position()
            return make_text(f"✅ {pc_name}: двойной клик здесь x={x}, y={y}")

        if cmd in {"left", "right", "up", "down"}:
            pixels = int(args.strip()) if args.strip() else 10
            pixels = max(1, min(500, pixels))
            dx = dy = 0
            if cmd == "left":
                dx = -pixels
            elif cmd == "right":
                dx = pixels
            elif cmd == "up":
                dy = -pixels
            else:
                dy = pixels
            x, y = nudge_mouse(dx, dy)
            return make_text(f"✅ {pc_name}: курсор {cmd} {pixels}px → x={x}, y={y}")

        if cmd == "type":
            if not args:
                return make_text("Пример: /type hello world")
            pyperclip.copy(args)
            pyautogui.hotkey("ctrl", "v")
            return make_text(f"✅ {pc_name}: вставил текст.")

        if cmd == "type_enter":
            if not args:
                return make_text("Пример: /type_enter hello world")
            pyperclip.copy(args)
            pyautogui.hotkey("ctrl", "v")
            pyautogui.press("enter")
            return make_text(f"✅ {pc_name}: вставил текст и нажал Enter.")

        if cmd == "enter":
            pyautogui.press("enter")
            return make_text(f"✅ {pc_name}: Enter.")

        if cmd == "backspace":
            count = int(args.strip()) if args.strip().isdigit() else 1
            count = max(1, min(count, 100))
            pyautogui.press("backspace", presses=count)
            return make_text(f"✅ {pc_name}: Backspace {count} раз.")

        if cmd == "ctrl_a":
            pyautogui.hotkey("ctrl", "a")
            return make_text(f"✅ {pc_name}: Ctrl+A.")

        if cmd == "key":
            key = normalize_key_name(args)
            pyautogui.press(key)
            return make_text(f"✅ {pc_name}: нажал клавишу {key}")

        if cmd == "hotkey":
            keys = parse_hotkey_args(args)
            pyautogui.hotkey(*keys)
            return make_text(f"✅ {pc_name}: {' + '.join(keys)}")

        if cmd == "key_down":
            key = normalize_key_name(args)
            pyautogui.keyDown(key)
            return make_text(f"✅ {pc_name}: зажал {key}. Отпустить: /key_up {key}")

        if cmd == "key_up":
            key = normalize_key_name(args)
            pyautogui.keyUp(key)
            return make_text(f"✅ {pc_name}: отпустил {key}")

        if cmd in {"esc", "space", "f5"}:
            key = "esc" if cmd == "esc" else cmd
            pyautogui.press(key)
            return make_text(f"✅ {pc_name}: {key}.")

        if cmd == "tab":
            count = int(args.strip()) if args.strip().isdigit() else 1
            count = max(1, min(count, 50))
            pyautogui.press("tab", presses=count)
            return make_text(f"✅ {pc_name}: Tab {count} раз.")

        hotkey_map = {
            "alt_tab": ("alt", "tab"),
            "ctrl_c": ("ctrl", "c"),
            "ctrl_v": ("ctrl", "v"),
            "ctrl_x": ("ctrl", "x"),
            "ctrl_z": ("ctrl", "z"),
            "ctrl_s": ("ctrl", "s"),
            "ctrl_f": ("ctrl", "f"),
            "ctrl_l": ("ctrl", "l"),
        }
        if cmd in hotkey_map:
            pyautogui.hotkey(*hotkey_map[cmd])
            return make_text(f"✅ {pc_name}: {'+'.join(hotkey_map[cmd])}.")

        return make_text(f"❓ Неизвестная команда: /{cmd}")

    except Exception as e:
        return make_text(f"⚠️ Ошибка в /{cmd} на {pc_name}:\n{e}")
