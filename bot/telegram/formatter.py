# bot/telegram/formatter.py
# Форматирование сообщений для Telegram (Markdown)

from datetime import datetime

from bot.monitor.server import ServerMonitor


def _status_emoji(percent: float) -> str:
    if percent < 60:
        return "🟢"
    elif percent < 80:
        return "🟡"
    return "🔴"


def format_status(monitor: ServerMonitor) -> str:
    cpu = monitor.get_cpu_usage()
    mem = monitor.get_memory_usage()
    disk = monitor.get_disk_usage()
    net = monitor.get_network_stats()
    uptime = monitor.get_uptime()
    load = monitor.get_load_average()
    services = monitor.get_running_services()
    ports = monitor.get_open_ports()

    lines = [
        "🖥 *СТАТУС СЕРВЕРА*",
        f"🕐 Обновлено: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"⏱ Аптайм: `{uptime}`",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "📊 *РЕСУРСЫ*",
        "",
        f"{_status_emoji(cpu)} *CPU:* `{cpu:.1f}%`",
        f"📈 Load: `{load}`",
        "",
        f"{_status_emoji(mem['percent'])} *RAM:* `{mem['percent']:.1f}%` "
        f"({mem['used']:.1f}/{mem['total']:.1f} GB)",
        "",
        f"{_status_emoji(disk['percent'])} *Disk:* `{disk['percent']:.1f}%` "
        f"({disk['used']:.1f}/{disk['total']:.1f} GB)",
        "",
        f"🌐 *Network:* ↓`{net['recv']:.1f} MB` ↑`{net['sent']:.1f} MB`",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🔧 *СЛУЖБЫ* (работает {len(services)})",
        "",
    ]

    for svc in services[:10]:
        lines.append(f"✅ `{svc['name']}`")
    if len(services) > 10:
        lines.append(f"_...и ещё {len(services) - 10} служб_")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🔌 *ОТКРЫТЫЕ ПОРТЫ* ({len(ports)})",
        "",
    ]
    for p in ports[:15]:
        lines.append(f"• Port `{p['port']}` — {p['process']}")
    if len(ports) > 15:
        lines.append(f"_...и ещё {len(ports) - 15} портов_")

    return "\n".join(lines)


def format_services(services: list) -> str:
    lines = ["🔧 *РАБОТАЮЩИЕ СЛУЖБЫ*", ""]
    for svc in services:
        lines.append(f"• `{svc['name']}` — {svc['status']}")
    if not services:
        lines.append("_Нет запущенных служб_")
    return "\n".join(lines)


def format_ports(ports: list) -> str:
    lines = ["🔌 *ОТКРЫТЫЕ ПОРТЫ*", ""]
    for p in ports:
        pid_info = f" \\[PID: {p['pid']}\\]" if p['pid'] else ""
        lines.append(f"• Port `{p['port']}` ({p['address']}) — {p['process']}{pid_info}")
    if not ports:
        lines.append("_Нет открытых портов_")
    return "\n".join(lines)


def format_ping(result: dict) -> str:
    host = result["host"]
    if result["success"]:
        if "avg" in result:
            return (
                f"🟢 *Ping {host}*\n\n"
                f"✅ Хост доступен\n"
                f"📊 Min: `{result['min']:.2f} ms`\n"
                f"📊 Avg: `{result['avg']:.2f} ms`\n"
                f"📊 Max: `{result['max']:.2f} ms`"
            )
        return f"🟢 *Ping {host}*\n\n✅ Хост доступен\n```\n{result['output']}\n```"
    error = result.get("error", "Хост недоступен")
    msg = f"🔴 *Ping {host}*\n\n❌ {error}"
    if "output" in result:
        msg += f"\n```\n{result['output']}\n```"
    return msg
