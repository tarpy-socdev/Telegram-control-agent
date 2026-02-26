#!/usr/bin/env python3
"""
update_bot.py — запусти этот скрипт на сервере чтобы обновить все файлы бота.
Использование: python3 update_bot.py
"""
import os, sys

BASE = "/opt/tg-control-agent"

FILES = {}

# ═══════════════════════════════════════════════════════════════════════════════
FILES["bot/storage/status_store.py"] = r"""
import json, os
from datetime import datetime

DEFAULT_SETTINGS = {
    "services_blacklist": ["getty@tty1","serial-getty@ttyS0","ModemManager",
                           "multipathd","osconfig","packagekit","qemu-guest-agent"],
    "services_filter": [], "ports_filter": [], "ports_blacklist": [],
    "show_services": True, "show_ports": True,
    "max_services": 10, "max_ports": 15,
    "alerts_enabled": False, "alert_cpu": 80, "alert_ram": 85, "alert_disk": 90,
    "daily_report_enabled": False, "daily_report_time": "09:00",
    "auto_reboot_enabled": False, "auto_reboot_time": "04:00",
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
        ch = self._data.get("channels", {})
        if str(chat_id) in ch:
            del ch[str(chat_id)]
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

    def record_stats(self, cpu, ram, disk, net_recv, net_sent):
        today = datetime.now().strftime("%Y-%m-%d")
        if "daily_stats" not in self._data:
            self._data["daily_stats"] = {}
        d = self._data["daily_stats"].get(today, {
            "cpu_max": 0, "ram_max": 0, "disk_max": 0,
            "net_recv_start": net_recv, "net_sent_start": net_sent,
            "net_recv_last": net_recv, "net_sent_last": net_sent,
        })
        d["cpu_max"] = max(d.get("cpu_max", 0), cpu)
        d["ram_max"] = max(d.get("ram_max", 0), ram)
        d["disk_max"] = max(d.get("disk_max", 0), disk)
        d["net_recv_last"] = net_recv
        d["net_sent_last"] = net_sent
        self._data["daily_stats"][today] = d
        keys = sorted(self._data["daily_stats"].keys())
        for k in keys[:-7]:
            del self._data["daily_stats"][k]
        self._save()

    def get_daily_stats(self, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self._data.get("daily_stats", {}).get(date, None)
""".lstrip()

# ═══════════════════════════════════════════════════════════════════════════════
FILES["bot/core/controller.py"] = r"""
import subprocess

class SystemController:
    @staticmethod
    def service_action(action, name):
        if action not in {"start","stop","restart","status"}:
            return False, f"Недопустимое действие: {action}"
        try:
            r = subprocess.run(["systemctl", action, name], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return True, f"Сервис {name} успешно {action}"
            return False, r.stderr.strip() or f"Ошибка {action} {name}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def reboot_server():
        try:
            subprocess.Popen(["bash", "-c", "sleep 5 && shutdown -r now"])
            return True, "ok"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def clear_journal():
        try:
            r = subprocess.run(["journalctl","--vacuum-time=1d"], capture_output=True, text=True, timeout=60)
            return True, r.stdout.strip() or "Логи очищены"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def close_port(port):
        try:
            r = subprocess.run(["lsof","-ti",f":{port}"], capture_output=True, text=True, timeout=10)
            pids = [p for p in r.stdout.strip().splitlines() if p]
            if not pids:
                return False, f"Порт {port} не используется"
            for pid in pids:
                subprocess.run(["kill","-9",pid], timeout=5)
            return True, f"Порт {port} закрыт (процессов: {len(pids)})"
        except Exception as e:
            return False, str(e)
""".lstrip()

# ═══════════════════════════════════════════════════════════════════════════════
FILES["bot/telegram/keyboards.py"] = r"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Обновить статус", callback_data="cmd:refresh")],
        [InlineKeyboardButton("🔧 Службы", callback_data="cmd:services"),
         InlineKeyboardButton("🔌 Порты",  callback_data="cmd:ports")],
        [InlineKeyboardButton("🌐 Пинг",   callback_data="cmd:ping_prompt"),
         InlineKeyboardButton("📋 Логи",   callback_data="cmd:logs_prompt")],
        [InlineKeyboardButton("🔄 Перезапуск службы", callback_data="cmd:restart_prompt")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="cmd:settings"),
         InlineKeyboardButton("🔁 Reboot",    callback_data="cmd:reboot")],
    ])

def settings_keyboard(s):
    svc  = "✅ Службы"       if s["show_services"]        else "❌ Службы"
    pts  = "✅ Порты"        if s["show_ports"]           else "❌ Порты"
    alrt = "🔔 Алерты ВКЛ"  if s["alerts_enabled"]       else "🔕 Алерты ВЫКЛ"
    rep  = "📅 Отчёт ВКЛ"   if s["daily_report_enabled"] else "📅 Отчёт ВЫКЛ"
    rb   = "⏰ Авто-ребут ВКЛ" if s["auto_reboot_enabled"] else "⏰ Авто-ребут ВЫКЛ"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(svc,  callback_data="settings:toggle_services"),
         InlineKeyboardButton(pts,  callback_data="settings:toggle_ports")],
        [InlineKeyboardButton("📢 Отправить статус в канал", callback_data="settings:send_status")],
        [InlineKeyboardButton("🔗 Привязать этот чат",  callback_data="settings:add_channel"),
         InlineKeyboardButton("🗑 Отвязать чат",        callback_data="settings:remove_channel")],
        [InlineKeyboardButton(alrt, callback_data="settings:toggle_alerts")],
        [InlineKeyboardButton(rep,  callback_data="settings:toggle_report")],
        [InlineKeyboardButton(rb,   callback_data="settings:toggle_reboot")],
        [InlineKeyboardButton("🚫 Скрытые службы", callback_data="settings:blacklist_info")],
        [InlineKeyboardButton("⬅️ Главная",         callback_data="cmd:home")],
    ])

def confirm_keyboard(yes_data):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Да",    callback_data=yes_data),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
    ]])

def back_to_home():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Главная", callback_data="cmd:home"),
    ]])

def clear_logs_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑 Очистить journalctl", callback_data="clear_journalctl"),
        InlineKeyboardButton("❌ Отмена",               callback_data="cancel"),
    ]])
""".lstrip()

# ═══════════════════════════════════════════════════════════════════════════════
FILES["bot/telegram/formatter.py"] = r"""
from datetime import datetime

def _emo(p):
    return "🟢" if p < 60 else ("🟡" if p < 80 else "🔴")

def _fs(services, settings):
    bl = set(settings.get("services_blacklist", []))
    wl = settings.get("services_filter", [])
    if wl:
        return [s for s in services if s["name"] in wl]
    return [s for s in services if s["name"] not in bl]

def _fp(ports, settings):
    bl = set(settings.get("ports_blacklist", []))
    wl = settings.get("ports_filter", [])
    if wl:
        return [p for p in ports if p["port"] in wl]
    return [p for p in ports if p["port"] not in bl]

def format_status(monitor, settings=None):
    if settings is None:
        settings = {}
    cpu  = max(0.0, monitor.get_cpu_usage())
    mem  = monitor.get_memory_usage()
    disk = monitor.get_disk_usage()
    net  = monitor.get_network_stats()
    lines = [
        "🖥 *СТАТУС СЕРВЕРА*",
        f"🕐 `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"⏱ Аптайм: `{monitor.get_uptime()}`",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "📊 *РЕСУРСЫ*",
        "",
        f"{_emo(cpu)} *CPU:* `{cpu:.1f}%`  📈 Load: `{monitor.get_load_average()}`",
        f"{_emo(mem['percent'])} *RAM:* `{mem['percent']:.1f}%` ({mem['used']:.1f}/{mem['total']:.1f} GB)",
        f"{_emo(disk['percent'])} *Disk:* `{disk['percent']:.1f}%` ({disk['used']:.1f}/{disk['total']:.1f} GB)",
        f"🌐 *Net:* down `{net['recv']:.1f}MB`  up `{net['sent']:.1f}MB`",
    ]
    if settings.get("show_services", True):
        svcs  = _fs(monitor.get_running_services(), settings)
        max_s = settings.get("max_services", 10)
        lines += ["", "━━━━━━━━━━━━━━━━━━━━",
                  f"🔧 *СЛУЖБЫ* ({min(len(svcs),max_s)}/{len(svcs)})", ""]
        for s in svcs[:max_s]:
            lines.append(f"✅ `{s['name']}`")
        if len(svcs) > max_s:
            lines.append(f"_...и ещё {len(svcs)-max_s}_")
    if settings.get("show_ports", True):
        ports = _fp(monitor.get_open_ports(), settings)
        max_p = settings.get("max_ports", 15)
        lines += ["", "━━━━━━━━━━━━━━━━━━━━",
                  f"🔌 *ПОРТЫ* ({len(ports)})", ""]
        for p in ports[:max_p]:
            lines.append(f"• `{p['port']}` — {p['process']}")
        if len(ports) > max_p:
            lines.append(f"_...и ещё {len(ports)-max_p}_")
    return "\n".join(lines)

def format_services(services, settings=None):
    if settings:
        services = _fs(services, settings)
    lines = [f"🔧 *СЛУЖБЫ* ({len(services)})", ""]
    for s in services:
        lines.append(f"• `{s['name']}` — {s['status']}")
    if not services:
        lines.append("_Нет запущенных служб_")
    return "\n".join(lines)

def format_ports(ports):
    lines = [f"🔌 *ОТКРЫТЫЕ ПОРТЫ* ({len(ports)})", ""]
    for p in ports:
        pid = f" [PID:{p['pid']}]" if p["pid"] else ""
        lines.append(f"• `{p['port']}` ({p['address']}) — {p['process']}{pid}")
    if not ports:
        lines.append("_Нет открытых портов_")
    return "\n".join(lines)

def format_ping(result):
    host = result["host"]
    if result["success"]:
        if "avg" in result:
            return (f"🟢 *Ping {host}*\n\n✅ Хост доступен\n"
                    f"Min: `{result['min']:.2f}ms` Avg: `{result['avg']:.2f}ms` Max: `{result['max']:.2f}ms`")
        return f"🟢 *Ping {host}*\n\n✅ Хост доступен"
    return f"🔴 *Ping {host}*\n\n❌ {result.get('error','Хост недоступен')}"

def format_daily_report(stats, date=None):
    if not stats:
        return "📊 *Дневной отчёт*\n\nДанных пока нет."
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    recv = stats.get("net_recv_last",0) - stats.get("net_recv_start",0)
    sent = stats.get("net_sent_last",0) - stats.get("net_sent_start",0)
    return "\n".join([
        f"📊 *ДНЕВНОЙ ОТЧЁТ* {date}",
        "",
        f"🔴 CPU макс: `{stats.get('cpu_max',0):.1f}%`",
        f"💾 RAM макс: `{stats.get('ram_max',0):.1f}%`",
        f"💿 Disk макс: `{stats.get('disk_max',0):.1f}%`",
        f"🌐 Трафик за день: down `{recv:.1f}MB`  up `{sent:.1f}MB`",
    ])
""".lstrip()

# ═══════════════════════════════════════════════════════════════════════════════
FILES["bot/telegram/handlers.py"] = r"""
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)
from bot.config import ADMIN_IDS
from bot.core.controller import SystemController
from bot.monitor.server import ServerMonitor
from bot.storage.status_store import StatusStore
from bot.telegram.formatter import (
    format_daily_report, format_ping, format_ports,
    format_services, format_status,
)
from bot.telegram.keyboards import (
    back_to_home, clear_logs_keyboard, confirm_keyboard,
    main_menu_keyboard, settings_keyboard,
)

def _is_admin(uid):
    return True if not ADMIN_IDS else uid in ADMIN_IDS

async def _deny(update):
    await update.message.reply_text("❌ Нет прав")

def _g(ctx, k):
    return ctx.bot_data[k]

async def _send_home(update, context):
    monitor  = _g(context, "monitor")
    store    = _g(context, "store")
    text     = format_status(monitor, store.get_settings())
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text, parse_mode="Markdown", reply_markup=main_menu_keyboard()
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text, parse_mode="Markdown", reply_markup=main_menu_keyboard()
            )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )

async def cmd_start(update, context):   await _send_home(update, context)
async def cmd_status(update, context):  await _send_home(update, context)
async def cmd_menu(update, context):    await _send_home(update, context)

async def cmd_ping(update, context):
    if not context.args:
        await update.message.reply_text("Использование: `/ping <хост>`", parse_mode="Markdown"); return
    host = context.args[0]
    await update.message.reply_text(f"🔄 Пингую `{host}`...", parse_mode="Markdown")
    result = _g(context, "monitor").ping_host(host)
    await update.message.reply_text(format_ping(result), parse_mode="Markdown", reply_markup=back_to_home())

async def cmd_services(update, context):
    monitor = _g(context, "monitor")
    store   = _g(context, "store")
    await update.message.reply_text(
        format_services(monitor.get_running_services(), store.get_settings()),
        parse_mode="Markdown", reply_markup=back_to_home()
    )

async def cmd_ports(update, context):
    await update.message.reply_text(
        format_ports(_g(context,"monitor").get_open_ports()),
        parse_mode="Markdown", reply_markup=back_to_home()
    )

async def cmd_restart_service(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    if not context.args:
        await update.message.reply_text("Использование: `/restart_service <имя>`", parse_mode="Markdown"); return
    name = context.args[0]
    await update.message.reply_text(
        f"⚠️ Перезапустить `{name}`?",
        reply_markup=confirm_keyboard(f"restart_service:{name}"), parse_mode="Markdown"
    )

async def cmd_reboot(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    await update.message.reply_text(
        "⚠️ *ВНИМАНИЕ!* Перезагрузить сервер?",
        reply_markup=confirm_keyboard("reboot_server"), parse_mode="Markdown"
    )

async def cmd_logs(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    if not context.args:
        await update.message.reply_text("Использование: `/logs <служба> [строк]`", parse_mode="Markdown"); return
    service = context.args[0]
    lines = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 50
    logs = _g(context, "monitor").get_logs(service, lines)
    if len(logs) > 3800:
        logs = logs[-3800:]
    await update.message.reply_text(
        f"📋 *Логи {service}:*\n```\n{logs}\n```",
        parse_mode="Markdown", reply_markup=back_to_home()
    )

async def cmd_clear_logs(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    await update.message.reply_text("⚠️ Очистить логи?", reply_markup=clear_logs_keyboard())

async def cmd_close_port(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Использование: `/close_port <порт>`", parse_mode="Markdown"); return
    port = int(context.args[0])
    await update.message.reply_text(
        f"⚠️ Закрыть порт `{port}`?",
        reply_markup=confirm_keyboard(f"close_port:{port}"), parse_mode="Markdown"
    )

async def cmd_test_update(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    await update.message.reply_text("🔄 Обновляю...")
    await _update_channels(context)
    await update.message.reply_text("✅ Готово!")

async def cmd_add_channel(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    monitor = _g(context, "monitor")
    store   = _g(context, "store")
    text    = format_status(monitor, store.get_settings())
    sent    = await update.message.reply_text(text, parse_mode="Markdown")
    store.add_channel(update.effective_chat.id, sent.message_id)
    await update.message.reply_text(
        f"✅ Чат `{update.effective_chat.id}` привязан!", parse_mode="Markdown"
    )

async def cmd_remove_channel(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    _g(context, "store").remove_channel(update.effective_chat.id)
    await update.message.reply_text("✅ Чат отвязан.")

async def cmd_broadcast(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    if not context.args:
        await update.message.reply_text("Использование: `/broadcast <текст>`", parse_mode="Markdown"); return
    text     = " ".join(context.args)
    store    = _g(context, "store")
    channels = store.get_channels()
    if not channels:
        await update.message.reply_text("❌ Нет привязанных каналов"); return
    count = 0
    for chat_id in channels:
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📢 {text}")
            count += 1
        except Exception as e:
            print(f"broadcast {chat_id}: {e}")
    await update.message.reply_text(f"✅ Отправлено в {count} канал(ов)")

async def cmd_set_blacklist(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    store = _g(context, "store")
    if not context.args:
        bl = store.get_settings()["services_blacklist"]
        await update.message.reply_text(
            f"Скрытые службы:\n`{', '.join(bl)}`\n\nИзменить: `/set_blacklist cron,dbus`",
            parse_mode="Markdown"
        ); return
    bl = [s.strip() for s in " ".join(context.args).split(",") if s.strip()]
    store.update_settings(services_blacklist=bl)
    await update.message.reply_text(f"✅ Обновлено: `{', '.join(bl)}`", parse_mode="Markdown")

async def cmd_report(update, context):
    store = _g(context, "store")
    stats = store.get_daily_stats()
    await update.message.reply_text(
        format_daily_report(stats), parse_mode="Markdown", reply_markup=back_to_home()
    )

async def cmd_set_report_time(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    if not context.args:
        await update.message.reply_text("Использование: `/set_report_time 09:00`", parse_mode="Markdown"); return
    _g(context, "store").update_settings(daily_report_time=context.args[0])
    await update.message.reply_text(f"✅ Время отчёта: `{context.args[0]}`", parse_mode="Markdown")

async def cmd_set_reboot_time(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    if not context.args:
        await update.message.reply_text("Использование: `/set_reboot_time 04:00`", parse_mode="Markdown"); return
    _g(context, "store").update_settings(auto_reboot_time=context.args[0])
    await update.message.reply_text(f"✅ Время авто-ребута: `{context.args[0]}`", parse_mode="Markdown")

async def cmd_set_alerts(update, context):
    if not _is_admin(update.effective_user.id): await _deny(update); return
    if len(context.args) < 3:
        await update.message.reply_text(
            "Использование: `/set_alerts <cpu> <ram> <disk>`\nПример: `/set_alerts 80 85 90`",
            parse_mode="Markdown"
        ); return
    cpu, ram, disk = int(context.args[0]), int(context.args[1]), int(context.args[2])
    _g(context, "store").update_settings(alert_cpu=cpu, alert_ram=ram, alert_disk=disk)
    await update.message.reply_text(
        f"✅ Пороги: CPU>{cpu}% RAM>{ram}% Disk>{disk}%", parse_mode="Markdown"
    )

async def handle_callbacks(update, context):
    query      = update.callback_query
    await query.answer()
    data       = query.data
    controller = _g(context, "controller")
    monitor    = _g(context, "monitor")
    store      = _g(context, "store")

    if data == "cancel":
        await query.edit_message_text("❌ Отменено"); return

    if data == "cmd:home":
        await _send_home(update, context); return

    if data == "cmd:refresh":
        text = format_status(monitor, store.get_settings())
        try:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
        except Exception:
            pass
        return

    if data == "cmd:services":
        await query.edit_message_text(
            format_services(monitor.get_running_services(), store.get_settings()),
            parse_mode="Markdown", reply_markup=back_to_home()
        ); return

    if data == "cmd:ports":
        await query.edit_message_text(
            format_ports(monitor.get_open_ports()),
            parse_mode="Markdown", reply_markup=back_to_home()
        ); return

    if data == "cmd:ping_prompt":
        await query.edit_message_text(
            "Введи в чат:\n`/ping google.com`", parse_mode="Markdown", reply_markup=back_to_home()
        ); return

    if data == "cmd:logs_prompt":
        await query.edit_message_text(
            "Введи в чат:\n`/logs nginx 50`", parse_mode="Markdown", reply_markup=back_to_home()
        ); return

    if data == "cmd:restart_prompt":
        await query.edit_message_text(
            "Введи в чат:\n`/restart_service nginx`", parse_mode="Markdown", reply_markup=back_to_home()
        ); return

    if data == "cmd:reboot":
        await query.edit_message_text(
            "⚠️ *ВНИМАНИЕ!* Перезагрузить сервер?",
            parse_mode="Markdown", reply_markup=confirm_keyboard("reboot_server")
        ); return

    if data == "cmd:settings":
        s  = store.get_settings()
        ch = store.get_channels()
        info = f"Привязано чатов: {len(ch)}" if ch else "Нет привязанных чатов"
        await query.edit_message_text(
            f"⚙️ *Настройки*\n\n{info}",
            parse_mode="Markdown", reply_markup=settings_keyboard(s)
        ); return

    if data == "settings:toggle_services":
        s = store.get_settings()
        store.update_settings(show_services=not s["show_services"])
        await query.edit_message_text("⚙️ *Настройки*", parse_mode="Markdown",
            reply_markup=settings_keyboard(store.get_settings())); return

    if data == "settings:toggle_ports":
        s = store.get_settings()
        store.update_settings(show_ports=not s["show_ports"])
        await query.edit_message_text("⚙️ *Настройки*", parse_mode="Markdown",
            reply_markup=settings_keyboard(store.get_settings())); return

    if data == "settings:toggle_alerts":
        s = store.get_settings()
        store.update_settings(alerts_enabled=not s["alerts_enabled"])
        s2 = store.get_settings()
        state = "включены" if s2["alerts_enabled"] else "выключены"
        await query.edit_message_text(
            f"⚙️ Алерты {state}.\nПороги: CPU>{s2['alert_cpu']}% RAM>{s2['alert_ram']}% Disk>{s2['alert_disk']}%\n\nИзменить: `/set_alerts 80 85 90`",
            parse_mode="Markdown", reply_markup=settings_keyboard(s2)
        ); return

    if data == "settings:toggle_report":
        s = store.get_settings()
        store.update_settings(daily_report_enabled=not s["daily_report_enabled"])
        s2 = store.get_settings()
        state = "включён" if s2["daily_report_enabled"] else "выключен"
        await query.edit_message_text(
            f"⚙️ Дневной отчёт {state}.\nВремя: `{s2['daily_report_time']}`\nИзменить: `/set_report_time 10:00`",
            parse_mode="Markdown", reply_markup=settings_keyboard(s2)
        ); return

    if data == "settings:toggle_reboot":
        s = store.get_settings()
        store.update_settings(auto_reboot_enabled=not s["auto_reboot_enabled"])
        s2 = store.get_settings()
        state = "включён" if s2["auto_reboot_enabled"] else "выключен"
        await query.edit_message_text(
            f"⚙️ Авто-ребут {state}.\nВремя: `{s2['auto_reboot_time']}`\nИзменить: `/set_reboot_time 04:00`",
            parse_mode="Markdown", reply_markup=settings_keyboard(s2)
        ); return

    if data == "settings:send_status":
        channels = store.get_channels()
        if not channels:
            await query.edit_message_text(
                "❌ Нет привязанных чатов.\nНажми *Привязать этот чат*.",
                parse_mode="Markdown", reply_markup=settings_keyboard(store.get_settings())
            ); return
        text  = format_status(monitor, store.get_settings())
        count = 0
        for chat_id in list(channels.keys()):
            try:
                sent = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
                store.add_channel(chat_id, sent.message_id)
                count += 1
            except Exception as e:
                print(f"send_status {chat_id}: {e}")
        await query.edit_message_text(
            f"✅ Статус отправлен в {count} чат(ов)",
            reply_markup=settings_keyboard(store.get_settings())
        ); return

    if data == "settings:add_channel":
        text = format_status(monitor, store.get_settings())
        sent = await context.bot.send_message(
            chat_id=query.message.chat_id, text=text, parse_mode="Markdown"
        )
        store.add_channel(query.message.chat_id, sent.message_id)
        await query.edit_message_text(
            f"✅ Чат `{query.message.chat_id}` привязан!",
            parse_mode="Markdown", reply_markup=settings_keyboard(store.get_settings())
        ); return

    if data == "settings:remove_channel":
        store.remove_channel(query.message.chat_id)
        await query.edit_message_text(
            "✅ Чат отвязан.", reply_markup=settings_keyboard(store.get_settings())
        ); return

    if data == "settings:blacklist_info":
        bl = ", ".join(store.get_settings()["services_blacklist"]) or "пусто"
        await query.edit_message_text(
            f"🚫 *Скрытые службы:*\n`{bl}`\n\nИзменить: `/set_blacklist cron,dbus`",
            parse_mode="Markdown", reply_markup=back_to_home()
        ); return

    if data.startswith("restart_service:"):
        name = data.split(":",1)[1]
        await query.edit_message_text(f"🔄 Перезапускаю `{name}`...", parse_mode="Markdown")
        ok, msg = controller.service_action("restart", name)
        await query.edit_message_text(
            f"{'✅' if ok else '❌'} {msg}", reply_markup=back_to_home()
        ); return

    if data == "reboot_server":
        ok, _ = controller.reboot_server()
        if ok:
            for chat_id in store.get_channels():
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🔁 *Сервер уходит на перезагрузку*\nБуду недоступен ~1 минуту.",
                        parse_mode="Markdown"
                    )
                except: pass
            await query.edit_message_text("🔁 Перезагружаюсь через 5 сек... До связи! 👋")
        else:
            await query.edit_message_text("❌ Ошибка перезагрузки")
        return

    if data == "clear_journalctl":
        await query.edit_message_text("🗑 Очищаю логи...")
        ok, msg = controller.clear_journal()
        await query.edit_message_text(f"{'✅' if ok else '❌'} {msg}", reply_markup=back_to_home()); return

    if data.startswith("close_port:"):
        port = int(data.split(":",1)[1])
        await query.edit_message_text(f"🔒 Закрываю порт {port}...")
        ok, msg = controller.close_port(port)
        await query.edit_message_text(f"{'✅' if ok else '❌'} {msg}", reply_markup=back_to_home()); return

async def handle_new_member(update, context):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            monitor = _g(context, "monitor")
            store   = _g(context, "store")
            text    = format_status(monitor, store.get_settings())
            sent    = await context.bot.send_message(
                chat_id=update.effective_chat.id, text=text, parse_mode="Markdown"
            )
            store.add_channel(update.effective_chat.id, sent.message_id)
            print(f"✅ Авто-добавлен в {update.effective_chat.id}")

async def _update_channels(context):
    monitor  = _g(context, "monitor")
    store    = _g(context, "store")
    settings = store.get_settings()
    text     = format_status(monitor, settings)
    cpu  = max(0.0, monitor.get_cpu_usage())
    mem  = monitor.get_memory_usage()
    disk = monitor.get_disk_usage()
    net  = monitor.get_network_stats()
    store.record_stats(cpu, mem["percent"], disk["percent"], net["recv"], net["sent"])
    for chat_id, message_id in list(store.get_channels().items()):
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=text, parse_mode="Markdown"
            )
        except Exception as e:
            err = str(e).lower()
            if "message to edit not found" in err or "message can't be edited" in err:
                try:
                    sent = await context.bot.send_message(
                        chat_id=chat_id, text=text, parse_mode="Markdown"
                    )
                    store.add_channel(chat_id, sent.message_id)
                    print(f"♻️ Переотправлен статус в {chat_id}")
                except Exception as e2:
                    print(f"⚠️ {chat_id}: {e2}")
            else:
                print(f"⚠️ {chat_id}: {e}")

async def job_update_status(context):
    await _update_channels(context)

async def job_alerts(context):
    store    = _g(context, "store")
    settings = store.get_settings()
    if not settings["alerts_enabled"]:
        return
    monitor = _g(context, "monitor")
    cpu  = max(0.0, monitor.get_cpu_usage())
    mem  = monitor.get_memory_usage()
    disk = monitor.get_disk_usage()
    alerts = []
    if cpu              > settings["alert_cpu"]:  alerts.append(f"🔴 CPU: `{cpu:.1f}%` (порог {settings['alert_cpu']}%)")
    if mem["percent"]   > settings["alert_ram"]:  alerts.append(f"🔴 RAM: `{mem['percent']:.1f}%` (порог {settings['alert_ram']}%)")
    if disk["percent"]  > settings["alert_disk"]: alerts.append(f"🔴 Disk: `{disk['percent']:.1f}%` (порог {settings['alert_disk']}%)")
    if not alerts:
        return
    text = "⚠️ *АЛЕРТ — Высокая нагрузка*\n\n" + "\n".join(alerts)
    for chat_id in store.get_channels():
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            print(f"alert {chat_id}: {e}")

async def job_daily_report(context):
    store    = _g(context, "store")
    settings = store.get_settings()
    if not settings["daily_report_enabled"]:
        return
    if datetime.now().strftime("%H:%M") != settings["daily_report_time"]:
        return
    stats = store.get_daily_stats()
    text  = format_daily_report(stats)
    for chat_id in store.get_channels():
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            print(f"report {chat_id}: {e}")

async def job_auto_reboot(context):
    store    = _g(context, "store")
    settings = store.get_settings()
    if not settings["auto_reboot_enabled"]:
        return
    if datetime.now().strftime("%H:%M") != settings["auto_reboot_time"]:
        return
    for chat_id in store.get_channels():
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ *Авто-перезагрузка* по расписанию ({settings['auto_reboot_time']})\nВернусь через ~1 минуту.",
                parse_mode="Markdown"
            )
        except: pass
    _g(context, "controller").reboot_server()

async def job_on_startup(context):
    store = _g(context, "store")
    for chat_id in store.get_channels():
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ *Бот снова онлайн!*\nСервер успешно перезагрузился.",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"startup {chat_id}: {e}")

def register_handlers(application):
    application.add_handler(CommandHandler("start",           cmd_start))
    application.add_handler(CommandHandler("menu",            cmd_menu))
    application.add_handler(CommandHandler("status",          cmd_status))
    application.add_handler(CommandHandler("services",        cmd_services))
    application.add_handler(CommandHandler("ports",           cmd_ports))
    application.add_handler(CommandHandler("ping",            cmd_ping))
    application.add_handler(CommandHandler("restart_service", cmd_restart_service))
    application.add_handler(CommandHandler("reboot",          cmd_reboot))
    application.add_handler(CommandHandler("logs",            cmd_logs))
    application.add_handler(CommandHandler("clear_logs",      cmd_clear_logs))
    application.add_handler(CommandHandler("close_port",      cmd_close_port))
    application.add_handler(CommandHandler("test_update",     cmd_test_update))
    application.add_handler(CommandHandler("add_channel",     cmd_add_channel))
    application.add_handler(CommandHandler("remove_channel",  cmd_remove_channel))
    application.add_handler(CommandHandler("broadcast",       cmd_broadcast))
    application.add_handler(CommandHandler("set_blacklist",   cmd_set_blacklist))
    application.add_handler(CommandHandler("report",          cmd_report))
    application.add_handler(CommandHandler("set_report_time", cmd_set_report_time))
    application.add_handler(CommandHandler("set_reboot_time", cmd_set_reboot_time))
    application.add_handler(CommandHandler("set_alerts",      cmd_set_alerts))
    application.add_handler(CallbackQueryHandler(handle_callbacks))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
""".lstrip()

# ═══════════════════════════════════════════════════════════════════════════════
FILES["bot/main.py"] = r"""
from telegram import Update
from telegram.ext import Application
from bot.config import BOT_TOKEN, UPDATE_INTERVAL
from bot.core.controller import SystemController
from bot.monitor.server import ServerMonitor
from bot.storage.status_store import StatusStore
from bot.telegram.handlers import (
    job_alerts, job_auto_reboot, job_daily_report,
    job_on_startup, job_update_status, register_handlers,
)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.bot_data["monitor"]    = ServerMonitor()
    application.bot_data["controller"] = SystemController()
    application.bot_data["store"]      = StatusStore()
    register_handlers(application)
    jq = application.job_queue
    jq.run_repeating(job_update_status, interval=UPDATE_INTERVAL, first=15)
    jq.run_repeating(job_alerts,        interval=60,  first=30)
    jq.run_repeating(job_daily_report,  interval=60,  first=60)
    jq.run_repeating(job_auto_reboot,   interval=60,  first=60)
    jq.run_once(job_on_startup, when=10)
    print(f"🤖 Бот запущен! Обновление каждые {UPDATE_INTERVAL} сек.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
""".lstrip()

# ═══════════════════════════════════════════════════════════════════════════════
# Записываем файлы
import ast

errors = 0
for path, content in FILES.items():
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    try:
        ast.parse(content)
    except SyntaxError as e:
        print(f"❌ СИНТАКСИС {path}: {e}")
        errors += 1
        continue
    with open(full, "w") as f:
        f.write(content)
    print(f"✅ {path}")

if errors:
    print(f"\n❌ Ошибок: {errors}")
    sys.exit(1)
else:
    print(f"\n✅ Все {len(FILES)} файлов записаны!")
