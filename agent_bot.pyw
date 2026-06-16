import asyncio
import base64
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from pc_actions import execute_local_command


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

ROLE = os.getenv("ROLE", "agent").strip().lower()
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
PC_NAME = os.getenv("PC_NAME", "agent").strip() or "agent"
AGENT_BOT_TOKEN = os.getenv("AGENT_BOT_TOKEN", "").strip()


def split_command(text: str):
    text = (text or "").strip()
    if not text.startswith("/"):
        return "", ""
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0].replace("/", "").lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    return cmd, args


def is_owner(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == OWNER_ID)


def marker(req_id: str):
    return f"[REQ:{req_id}]"


async def send_result(update: Update, req_id: str, result: dict):
    prefix = marker(req_id)
    kind = result.get("kind", "text")

    if kind == "text":
        text = result.get("text", "")
        await update.message.reply_text(f"{prefix}\n{text}"[:3900])
        return

    data_b64 = result.get("data_b64")
    filename = result.get("filename", "file.bin")
    caption = result.get("caption", "")
    if not data_b64:
        await update.message.reply_text(f"{prefix}\n⚠️ Пустой файл результата.")
        return

    data = base64.b64decode(data_b64.encode("ascii"))
    temp_path = Path(tempfile.gettempdir()) / filename
    temp_path.write_bytes(data)

    if kind == "photo":
        with open(temp_path, "rb") as f:
            await update.message.reply_photo(photo=f, caption=f"{prefix}\n{caption}"[:1024])
    else:
        with open(temp_path, "rb") as f:
            await update.message.reply_document(document=f, filename=filename, caption=f"{prefix}\n{caption}"[:1024])


async def agent_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not is_owner(update):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    text = update.message.text or update.message.caption or ""
    cmd, args = split_command(text)

    if cmd == "start":
        await update.message.reply_text(f"✅ Agent online: {PC_NAME}")
        return

    if cmd == "pc":
        await update.message.reply_text(f"💻 PC_NAME: {PC_NAME}")
        return

    if cmd not in {"__pcbot", "__pcbot_file"}:
        await update.message.reply_text(
            f"✅ Agent {PC_NAME} работает.\n"
            "Команды обычно приходят через main relay.\n"
            "Проверка: /pc"
        )
        return

    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("⚠️ Неверный relay формат.")
        return

    req_id = parts[0].strip()
    command_line = parts[1].strip()

    file_payload = None
    if cmd == "__pcbot_file":
        doc = update.message.document
        if not doc:
            await update.message.reply_text(f"{marker(req_id)}\n⚠️ Файл не найден в сообщении.")
            return

        tg_file = await doc.get_file()
        temp_path = Path(tempfile.gettempdir()) / f"agent_upload_{doc.file_unique_id}_{doc.file_name}"
        await tg_file.download_to_drive(custom_path=str(temp_path))
        file_payload = {
            "filename": doc.file_name,
            "data_b64": base64.b64encode(temp_path.read_bytes()).decode("ascii"),
        }

    result = await asyncio.to_thread(execute_local_command, PC_NAME, command_line, file_payload)
    await send_result(update, req_id, result)


async def notify_startup(app):
    try:
        await app.bot.send_message(chat_id=OWNER_ID, text=f"🟢 Agent запущен: {PC_NAME}")
    except Exception:
        pass


def main():
    if ROLE != "agent":
        raise RuntimeError("Этот файл запускается только при ROLE=agent")

    if not AGENT_BOT_TOKEN or OWNER_ID == 0:
        raise RuntimeError("Заполни AGENT_BOT_TOKEN и OWNER_ID в .env")

    # Вечный цикл: если интернет/Telegram временно упал или polling завершился,
    # agent не выключается, а пробует подняться снова.
    while True:
        try:
            app = ApplicationBuilder().token(AGENT_BOT_TOKEN).post_init(notify_startup).build()
            app.add_handler(MessageHandler(filters.COMMAND | filters.Document.ALL, agent_router))
            app.run_polling(drop_pending_updates=False)
        except Exception:
            import time
            time.sleep(10)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main()
