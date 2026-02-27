#!/usr/bin/env python3
"""
create_bot_files.py — создает ВСЕ файлы бота в /opt/tg-control-agent
Запусти: python3 create_bot_files.py
"""

import os
import sys

BOT_DIR = "/opt/tg-control-agent"

# Создаём структуру папок
os.makedirs(f"{BOT_DIR}/bot/core", exist_ok=True)
os.makedirs(f"{BOT_DIR}/bot/monitor", exist_ok=True)
os.makedirs(f"{BOT_DIR}/bot/storage", exist_ok=True)
os.makedirs(f"{BOT_DIR}/bot/telegram", exist_ok=True)

print("📁 Структура папок создана")

# ═════════════════════════════════════════════════════════════════════════════
# ФАЙЛЫ КОТОРЫЕ БУДУТ СОЗДАНЫ

FILES = {
    ".env.example": """# Telegram Bot Token от @BotFather
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# ID администраторов (через запятую)
ADMIN_IDS=YOUR_ADMIN_ID

# Интервал обновления статуса в секундах (минимум 30)
UPDATE_INTERVAL=30
""",

    "requirements.txt": """python-telegram-bot==20.7
psutil==5.9.6
python-dotenv==1.0.0
""",

    "bot/__init__.py": "",
    "bot/core/__init__.py": "",
    "bot/monitor/__init__.py": "",
    "bot/storage/__init__.py": "",
    "bot/telegram/__init__.py": "",

    "bot/config.py": """import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "30"))
""",

    "bot/main.py": """import os
import sys
import asyncio
from datetime import datetime
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler

sys.path.insert(0, os.path.dirname(__file__))

from bot.config import BOT_TOKEN, UPDATE_INTERVAL
from bot.monitor.server import ServerMonitor
from bot.storage.status_store import StatusStore
from bot.core.controller import SystemController
from bot.telegram.handlers import register_handlers

async def main():
    print(f"🤖 Бот запущен! Обновление каждые {UPDATE_INTERVAL} сек.")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Инициализируем компоненты
    app.bot_data["monitor"] = ServerMonitor()
    app.bot_data["store"] = StatusStore()
    app.bot_data["controller"] = SystemController()
    
    # Регистрируем все обработчики
    register_handlers(app)
    
    # Запускаем polling
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
""",

    "bot/monitor/server.py": """import psutil
import subprocess
from datetime import datetime

class ServerMonitor:
    def __init__(self):
        self.start_time = datetime.now()
    
    def get_cpu_usage(self):
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self):
        mem = psutil.virtual_memory()
        return {
            "percent": mem.percent,
            "used": mem.used / (1024**3),
            "total": mem.total / (1024**3)
        }
    
    def get_disk_usage(self):
        disk = psutil.disk_usage("/")
        return {
            "percent": disk.percent,
            "used": disk.used / (1024**3),
            "total": disk.total / (1024**3)
        }
    
    def get_load_average(self):
        load = psutil.getloadavg()
        return f"{load[0]:.2f} {load[1]:.2f} {load[2]:.2f}"
    
    def get_uptime(self):
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        days = uptime.days
        hours = uptime.seconds // 3600
        mins = (uptime.seconds % 3600) // 60
        return f"{days}д {hours}ч {mins}м"
    
    def get_network_stats(self):
        net = psutil.net_io_counters()
        return {
            "recv": net.bytes_recv / (1024**2),
            "sent": net.bytes_sent / (1024**2)
        }
    
    def get_running_services(self):
        try:
            result = subprocess.run(["systemctl", "list-units", "--type=service", "--state=running", "--no-pager", "--plain"], 
                                  capture_output=True, text=True, timeout=10)
            services = []
            for line in result.stdout.strip().split("\\n"):
                if line:
                    parts = line.split()
                    if parts:
                        services.append({"name": parts[0].replace(".service", ""), "status": "active"})
            return services[:20]
        except:
            return []
    
    def get_open_ports(self):
        try:
            result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=10)
            ports = []
            for line in result.stdout.strip().split("\\n")[1:]:
                if line:
                    parts = line.split()
                    if len(parts) >= 4:
                        addr = parts[3]
                        if ":" in addr:
                            port = addr.split(":")[-1]
                            process = parts[-1] if len(parts) > 5 else "unknown"
                            ports.append({"port": port, "address": addr, "process": process, "pid": None})
            return ports[:15]
        except:
            return []
    
    def get_logs(self, service, lines=50):
        try:
            result = subprocess.run(["journalctl", "-u", service, "-n", str(lines), "--no-pager"],
                                  capture_output=True, text=True, timeout=15)
            return result.stdout or "No logs found"
        except:
            return "Error reading logs"
    
    def ping_host(self, host):
        try:
            result = subprocess.run(["ping", "-c", "4", host], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split("\\n")
                stats_line = [l for l in lines if "min/avg/max" in l]
                if stats_line:
                    parts = stats_line[0].split("=")[1].split("/")
                    return {
                        "host": host,
                        "success": True,
                        "min": float(parts[0]),
                        "avg": float(parts[1]),
                        "max": float(parts[2])
                    }
            return {"host": host, "success": False, "error": "Host unreachable"}
        except:
            return {"host": host, "success": False, "error": "Ping failed"}
""",

    "bot/core/controller.py": """import os
import subprocess

class SystemController:
    @staticmethod
    def service_action(action, name):
        if action not in {"start","stop","restart","status"}:
            return False, f"Недопустимое действие: {action}"
        try:
            r = subprocess.run(["systemctl", action, name], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return True, f"✅ Сервис {name}: {action} выполнен"
            return False, r.stderr.strip() or f"Ошибка {action} {name}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def ssh_disable():
        try:
            subprocess.run(["systemctl","stop","ssh.socket"], timeout=10)
            subprocess.run(["systemctl","stop","ssh"], timeout=10)
            subprocess.run(["systemctl","disable","ssh.socket"], timeout=10)
            subprocess.run(["systemctl","disable","ssh"], timeout=10)
            return True, "🔴 SSH полностью отключен"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def ssh_enable():
        try:
            subprocess.run(["systemctl","enable","ssh.socket"], timeout=10)
            subprocess.run(["systemctl","enable","ssh"], timeout=10)
            subprocess.run(["systemctl","start","ssh.socket"], timeout=10)
            return True, "🟢 SSH включен"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def reboot_server():
        try:
            subprocess.Popen(["bash","-c","sleep 5 && shutdown -r now"])
            return True, "ok"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def clear_journal():
        try:
            r = subprocess.run(["journalctl","--vacuum-time=1d"], capture_output=True, text=True, timeout=60)
            return True, "✅ Логи очищены"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def close_port(port):
        try:
            r = subprocess.run(["lsof","-ti",f":{port}"], capture_output=True, text=True, timeout=10)
            pids = [p for p in r.stdout.strip().splitlines() if p]
            if not pids:
                return False, f"❌ Порт {port} не используется"
            for pid in pids:
                subprocess.run(["kill","-9",pid], timeout=5)
            return True, f"✅ Порт {port} закрыт (процессов: {len(pids)})"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def add_ssh_key(pubkey, username="root"):
        try:
            import pwd
            try:
                pw = pwd.getpwnam(username)
                home = pw.pw_dir
                uid, gid = pw.pw_uid, pw.pw_gid
            except KeyError:
                home = "/root"
                uid = gid = 0
            
            ssh_dir = f"{home}/.ssh"
            auth_file = f"{ssh_dir}/authorized_keys"
            
            os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
            os.chown(ssh_dir, uid, gid)
            
            existing = open(auth_file).read() if os.path.exists(auth_file) else ""
            if pubkey.strip() in existing:
                return False, f"⚠️ Ключ уже добавлен для {username}"
            
            with open(auth_file, "a") as f:
                f.write(f"\\n{pubkey.strip()}\\n")
            
            os.chmod(auth_file, 0o600)
            os.chown(auth_file, uid, gid)
            
            return True, f"✅ SSH ключ добавлен для пользователя {username}"
        except Exception as e:
            return False, f"❌ Ошибка: {str(e)}"
""",

    "bot/storage/status_store.py": """import json
import os
from datetime import datetime, timedelta

DEFAULT_SETTINGS = {
    "show_services": True,
    "show_ports": True,
    "alerts_enabled": False,
    "alert_cpu": 80,
    "alert_ram": 85,
    "alert_disk": 90,
    "daily_report_enabled": False,
    "daily_report_time": "09:00",
    "auto_reboot_enabled": False,
    "auto_reboot_time": "04:00",
    "max_services": 10,
    "max_ports": 15,
    "services_blacklist": ["getty@tty1","serial-getty@ttyS0","ModemManager",
                           "multipathd","osconfig","packagekit","qemu-guest-agent"],
}

class StatusStore:
    def __init__(self, filename="status_messages.json"):
        self.filename = filename
        self._data = self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename) as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save(self):
        with open(self.filename, "w") as f:
            json.dump(self._data, f, indent=2)

    def add_channel(self, chat_id, message_id):
        if "channels" not in self._data:
            self._data["channels"] = {}
        self._data["channels"][str(chat_id)] = message_id
        self._save()

    def get_channels(self):
        return {int(k): v for k, v in self._data.get("channels", {}).items()}

    def remove_channel(self, chat_id):
        if "channels" in self._data and str(chat_id) in self._data["channels"]:
            del self._data["channels"][str(chat_id)]
            self._save()

    def get_settings(self):
        s = DEFAULT_SETTINGS.copy()
        s.update(self._data.get("settings", {}))
        return s

    def update_settings(self, **kwargs):
        if "settings" not in self._data:
            self._data["settings"] = {}
        self._data["settings"].update(kwargs)
        self._save()
""",

    "bot/telegram/handlers.py": """from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🖥️ БОТ МОНИТОРИНГА СЕРВЕРА\\n\\nБот запущен и работает!")

def register_handlers(app):
    app.add_handler(CommandHandler("start", cmd_start))
""",

    "bot/telegram/keyboards.py": """from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статус", callback_data="cmd:status"),
         InlineKeyboardButton("🔧 Службы", callback_data="cmd:services")],
        [InlineKeyboardButton("🔌 Порты", callback_data="cmd:ports"),
         InlineKeyboardButton("🔁 Reboot", callback_data="cmd:reboot")],
    ])
""",

    "bot/telegram/formatter.py": """def format_status(monitor, settings=None):
    cpu = max(0.0, monitor.get_cpu_usage())
    mem = monitor.get_memory_usage()
    return f"""🖥️ СТАТУС СЕРВЕРА

CPU: {cpu:.1f}%
RAM: {mem['percent']:.1f}%
"""
""",
}

# ═════════════════════════════════════════════════════════════════════════════
# СОЗДАЁМ ВСЕ ФАЙЛЫ

os.chdir(BOT_DIR)

for filepath, content in FILES.items():
    full_path = os.path.join(BOT_DIR, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(full_path, "w") as f:
        f.write(content)
    
    print(f"✅ {filepath}")

print("")
print("════════════════════════════════════════════════════════════")
print("✨ ВСЕ ФАЙЛЫ СОЗДАНЫ!")
print("════════════════════════════════════════════════════════════")
print("")
print("📋 Следующие шаги:")
print("")
print("1️⃣ Отредактируй конфиг:")
print(f"   nano {BOT_DIR}/.env")
print("   Вбей свой BOT_TOKEN и ADMIN_IDS")
print("")
print("2️⃣ Установи бота:")
print(f"   cd {BOT_DIR}")
print("   sudo chmod +x install.sh")
print("   sudo ./install.sh install")
print("")
print("3️⃣ Запусти:")
print("   sudo ./install.sh start")
print("")
print("4️⃣ Проверь логи:")
print("   sudo ./install.sh logs 20")
print("")
print("════════════════════════════════════════════════════════════")
