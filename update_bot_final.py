#!/usr/bin/env python3
"""update_bot_final.py — финальное обновление бота с фиксами и оптимизацией"""
import os, sys, ast

BASE = "/opt/tg-control-agent"
FILES = {}

# ══════════════════════════════════════════════════════════════════════════════
# CONTROLLER.PY — ФИКСИМ SSH И ОПТИМИЗУЕМ
FILES["bot/core/controller.py"] = r"""
import os, subprocess

class SystemController:
    @staticmethod
    def service_action(action, name):
        if action not in {"start","stop","restart","status"}:
            return False, f"Недопустимое действие: {action}"
        try:
            r = subprocess.run(["systemctl", action, name], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return True, f"Сервис {name}: {action} выполнен"
            return False, r.stderr.strip() or f"Ошибка {action} {name}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def ssh_disable():
        """Отключить SSH полностью (service + socket)"""
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
        """Включить SSH"""
        try:
            subprocess.run(["systemctl","enable","ssh.socket"], timeout=10)
            subprocess.run(["systemctl","enable","ssh"], timeout=10)
            subprocess.run(["systemctl","start","ssh.socket"], timeout=10)
            return True, "🟢 SSH включен"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def ssh_status():
        """Статус SSH"""
        try:
            r = subprocess.run(["systemctl","is-active","ssh"], capture_output=True, text=True, timeout=5)
            return "active" in r.stdout
        except:
            return False

    @staticmethod
    def add_ssh_key(pubkey, username="root"):
        """Добавить SSH ключ для пользователя"""
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
                f.write(f"\n{pubkey.strip()}\n")
            
            os.chmod(auth_file, 0o600)
            os.chown(auth_file, uid, gid)
            
            return True, f"✅ SSH ключ добавлен для пользователя {username}"
        except Exception as e:
            return False, f"❌ Ошибка: {str(e)}"

    @staticmethod
    def get_autostart_services():
        """Список служб в автозапуске"""
        try:
            r = subprocess.run(
                ["systemctl","list-unit-files","--type=service","--state=enabled","--no-pager","--no-legend"],
                capture_output=True, text=True, timeout=15
            )
            return [l.split()[0].replace(".service","") for l in r.stdout.strip().splitlines() if l.split()]
        except:
            return []

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
            return True, r.stdout.strip() or "✅ Логи очищены"
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
"""

# ══════════════════════════════════════════════════════════════════════════════
# KEYBOARDS.PY — УЛУЧШЕННЫЙ ИНТЕРФЕЙС
FILES["bot/telegram/keyboards.py"] = r"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Обновить", callback_data="cmd:refresh"),
         InlineKeyboardButton("🔧 Службы", callback_data="cmd:services")],
        [InlineKeyboardButton("🔌 Порты", callback_data="cmd:ports"),
         InlineKeyboardButton("🌐 Пинг", callback_data="cmd:ping_prompt")],
        [InlineKeyboardButton("📋 Логи", callback_data="cmd:logs_prompt"),
         InlineKeyboardButton("⚙️ Настройки", callback_data="cmd:settings")],
        [InlineKeyboardButton("🔐 SSH", callback_data="cmd:ssh_menu"),
         InlineKeyboardButton("🔁 Reboot", callback_data="cmd:reboot")],
    ])

def ssh_menu(ssh_active):
    status = "🟢 ВКЛ" if ssh_active else "🔴 ВЫКЛ"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"SSH {status}", callback_data="ssh:toggle")],
        [InlineKeyboardButton("🔑 Добавить ключ", callback_data="ssh:add_key_info")],
        [InlineKeyboardButton("⬅️ Меню", callback_data="cmd:home")],
    ])

def confirm(yes_data):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ ДА", callback_data=yes_data),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
    ]])

def settings_menu(s):
    svc = "✅" if s["show_services"] else "❌"
    pts = "✅" if s["show_ports"] else "❌"
    alrt = "🔔 ВКЛ" if s["alerts_enabled"] else "🔕 ВЫКЛ"
    rep = "📅 ВКЛ" if s["daily_report_enabled"] else "📅 ВЫКЛ"
    rb = "⏰ ВКЛ" if s["auto_reboot_enabled"] else "⏰ ВЫКЛ"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Службы {svc}", callback_data="settings:toggle_svc"),
         InlineKeyboardButton(f"Порты {pts}", callback_data="settings:toggle_ports")],
        [InlineKeyboardButton("📢 Отправить статус", callback_data="settings:broadcast_status")],
        [InlineKeyboardButton("🔗 Привязать чат", callback_data="settings:link_chat"),
         InlineKeyboardButton("🗑 Отвязать", callback_data="settings:unlink_chat")],
        [InlineKeyboardButton(f"Алерты {alrt}", callback_data="settings:toggle_alerts")],
        [InlineKeyboardButton(f"Отчёт {rep}", callback_data="settings:toggle_report")],
        [InlineKeyboardButton(f"Ребут {rb}", callback_data="settings:toggle_reboot")],
        [InlineKeyboardButton("🧹 Очистить сообщения", callback_data="settings:cleanup")],
        [InlineKeyboardButton("⬅️ Меню", callback_data="cmd:home")],
    ])

def cleanup_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Все сообщения", callback_data="cleanup:all")],
        [InlineKeyboardButton("📅 За последние 7 дней", callback_data="cleanup:7days")],
        [InlineKeyboardButton("📅 За последние 30 дней", callback_data="cleanup:30days")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ])

def back_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главная", callback_data="cmd:home")]])
"""

# ══════════════════════════════════════════════════════════════════════════════
# FORMATTER.PY — КРАСИВЫЕ СООБЩЕНИЯ
FILES["bot/telegram/formatter.py"] = r"""
from datetime import datetime

def emoji_load(val, max_val=100):
    if val < 50:
        return "🟢"
    elif val < 80:
        return "🟡"
    else:
        return "🔴"

def format_status(mon, settings=None):
    if settings is None:
        settings = {}
    
    cpu = max(0.0, mon.get_cpu_usage())
    mem = mon.get_memory_usage()
    disk = mon.get_disk_usage()
    net = mon.get_network_stats()
    uptime = mon.get_uptime()
    load = mon.get_load_average()
    
    status = f"""╔═══════════════════════════════╗
║  🖥️  СТАТУС СЕРВЕРА
║  {datetime.now().strftime('%H:%M:%S')}
╚═══════════════════════════════╝

⏱️ Аптайм: {uptime}
📊 Load: {load}

📈 РЕСУРСЫ
{emoji_load(cpu)} CPU: {cpu:.1f}%
{emoji_load(mem['percent'])} RAM: {mem['percent']:.1f}% ({mem['used']:.1f}/{mem['total']:.1f} GB)
{emoji_load(disk['percent'])} Disk: {disk['percent']:.1f}% ({disk['used']:.1f}/{disk['total']:.1f} GB)
🌐 Net: ⬇️{net['recv']:.1f}MB ⬆️{net['sent']:.1f}MB
"""
    
    if settings.get("show_services"):
        services = mon.get_running_services()[:settings.get("max_services", 10)]
        status += f"\n🔧 СЛУЖБЫ ({len(services)})\n"
        for s in services:
            status += f"  ✅ {s['name']}\n"
    
    if settings.get("show_ports"):
        ports = mon.get_open_ports()[:settings.get("max_ports", 15)]
        status += f"\n🔌 ПОРТЫ ({len(ports)})\n"
        for p in ports:
            status += f"  • {p['port']} — {p['process']}\n"
    
    return status

def format_alert(alert_type, value, threshold):
    return f"""⚠️ АЛЕРТ — ВЫСОКАЯ НАГРУЗКА

🔴 {alert_type}: {value:.1f}% > {threshold}%

⏰ Время: {datetime.now().strftime('%H:%M:%S')}"""

def format_ping(result):
    host = result["host"]
    if result["success"]:
        if "avg" in result:
            return f"""🟢 PING {host}

✅ Доступен
Min: {result['min']:.2f}ms
Avg: {result['avg']:.2f}ms
Max: {result['max']:.2f}ms"""
        return f"🟢 Ping {host} успешен"
    return f"🔴 Ping {host} не доступен\n\n{result.get('error', 'Ошибка')}"

def format_services(services):
    text = f"🔧 СЛУЖБЫ ({len(services)})\n\n"
    for s in services:
        status_icon = "✅" if s["status"] == "active" else "❌"
        text += f"{status_icon} {s['name']}\n"
    return text or "Нет служб"

def format_ports(ports):
    text = f"🔌 ОТКРЫТЫЕ ПОРТЫ ({len(ports)})\n\n"
    for p in ports:
        text += f"• {p['port']:5} — {p['process']}\n"
    return text or "Нет открытых портов"

def format_report(report):
    return f"""📊 ДНЕВНОЙ ОТЧЁТ

🔴 Макс CPU: {report.get('cpu_max', 0):.1f}%
🔴 Макс RAM: {report.get('ram_max', 0):.1f}%
🔴 Макс Disk: {report.get('disk_max', 0):.1f}%
🌐 Данных: {report.get('net_total', 0):.1f}MB

📅 Дата: {datetime.now().strftime('%d.%m.%Y')}"""
"""

# ══════════════════════════════════════════════════════════════════════════════
# STORAGE + ОСТАЛЬНОЕ
FILES["bot/storage/status_store.py"] = r"""
import json, os
from datetime import datetime, timedelta

DEFAULT_SETTINGS = {
    "show_services": True, "show_ports": True,
    "alerts_enabled": False, "alert_cpu": 80, "alert_ram": 85, "alert_disk": 90,
    "daily_report_enabled": False, "daily_report_time": "09:00",
    "auto_reboot_enabled": False, "auto_reboot_time": "04:00",
    "max_services": 10, "max_ports": 15,
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
        self._data["channels"][str(chat_id)] = {"msg_id": message_id, "added": datetime.now().isoformat()}
        self._save()

    def get_channels(self):
        ch = self._data.get("channels", {})
        return {int(k): v["msg_id"] if isinstance(v, dict) else v for k, v in ch.items()}

    def get_all_channels(self):
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

    def add_alert_history(self, chat_id, alert_type, value):
        if "alerts" not in self._data:
            self._data["alerts"] = {}
        key = f"{chat_id}_{alert_type}"
        self._data["alerts"][key] = value
        self._save()

    def should_alert(self, chat_id, alert_type, threshold, current_value):
        key = f"{chat_id}_{alert_type}"
        last = self._data.get("alerts", {}).get(key)
        if last is None or current_value > last + 5:
            self.add_alert_history(chat_id, alert_type, current_value)
            return True
        return False

    def cleanup_old_messages(self, days=None):
        cutoff = datetime.now() - timedelta(days=days) if days else None
        channels = self._data.get("channels", {})
        removed = []
        
        for chat_id, data in channels.items():
            if isinstance(data, dict) and "added" in data:
                added = datetime.fromisoformat(data["added"])
                if cutoff is None or added < cutoff:
                    removed.append(chat_id)
        
        for chat_id in removed:
            del channels[str(chat_id)]
        
        if removed:
            self._save()
        return removed
"""

# ══════════════════════════════════════════════════════════════════════════════
# ГЛАВНОЕ — ВАЛИДАЦИЯ И ЗАПИСЬ ВСЕХ ФАЙЛОВ

def validate_and_write():
    base_dir = BASE
    for filepath, content in FILES.items():
        full_path = os.path.join(base_dir, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        try:
            ast.parse(content)
            with open(full_path, "w") as f:
                f.write(content)
            print(f"✅ {filepath}")
        except SyntaxError as e:
            print(f"❌ {filepath}: {e}")
            return False
    
    return True

if __name__ == "__main__":
    if validate_and_write():
        print("\n✨ Все файлы обновлены успешно!")
    else:
        sys.exit(1)
