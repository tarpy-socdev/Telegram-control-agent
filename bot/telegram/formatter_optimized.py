"""
Оптимизированный форматер вывода с эмодзи
Снижает нагрузку на систему кешированием и минимизирует объёмы передачи данных
"""
from datetime import datetime
from functools import lru_cache

# ============================================================================
# Status indicators с эмодзи для лучшей визуализации
# ============================================================================

@lru_cache(maxsize=1)
def _get_status_emoji(metric_type: str, value: float) -> str:
    """Кешированное получение эмодзи в зависимости от метрики"""
    if metric_type == "cpu":
        if value < 50:  return "🟢"      # зелёный — нормально
        if value < 75:  return "🟡"      # жёлтый — внимание
        if value < 90:  return "🟠"      # оранжевый — критично
        return "🔴"                      # красный — опасно
    
    elif metric_type == "memory":
        if value < 60:  return "🟢"
        if value < 80:  return "🟡"
        return "🔴"
    
    elif metric_type == "disk":
        if value < 70:  return "🟢"
        if value < 85:  return "🟡"
        if value < 95:  return "🟠"
        return "🔴"
    
    return "⚪"


def _bar(p, width=8):
    """ASCII прогресс-бар: [████░░░░]"""
    filled = round(p / 100 * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def _flt_svc(svcs, s):
    """Фильтр сервисов по настройкам"""
    mode = s.get("services_mode", "filtered")
    if mode == "all":
        return svcs
    if mode == "custom":
        wl = set(s.get("services_filter", []))
        return [x for x in svcs if x["name"] in wl]
    bl = set(s.get("services_blacklist", []))
    return [x for x in svcs if x["name"] not in bl]


def _flt_ports(ports, s):
    """Фильтр портов по настройкам"""
    bl = set(s.get("ports_blacklist", []))
    wl = s.get("ports_filter", [])
    if wl:
        return [p for p in ports if p["port"] in wl]
    return [p for p in ports if p["port"] not in bl]


# ============================================================================
# Основные форматеры
# ============================================================================

def format_status(monitor, settings=None):
    """
    Основной статус сервера с эмодзи и оптимизированным форматом.
    Минимизирует размер и улучшает читаемость
    """
    s   = settings or {}
    cpu = max(0.0, monitor.get_cpu_usage())
    mem = monitor.get_memory_usage()
    dsk = monitor.get_disk_usage()
    net = monitor.get_network_stats()

    # Основная статистика с эмодзи
    lines = [
        "📊 *SERVER STATUS*",
        f"🕐 `{datetime.now().strftime('%H:%M:%S')}`  ⏱ {monitor.get_uptime()}",
        "",
    ]

    # CPU с цветным индикатором
    cpu_emoji = _get_status_emoji("cpu", cpu)
    lines.append(f"{cpu_emoji} CPU {_bar(cpu)} `{cpu:.1f}%` • load `{monitor.get_load_average()}`")
    
    # RAM с цветным индикатором
    mem_emoji = _get_status_emoji("memory", mem['percent'])
    lines.append(f"{mem_emoji} RAM {_bar(mem['percent'])} `{mem['percent']:.1f}%` • `{mem['used']:.1f}/{mem['total']:.1f}GB`")
    
    # Disk с цветным индикатором
    dsk_emoji = _get_status_emoji("disk", dsk['percent'])
    lines.append(f"{dsk_emoji} DISK {_bar(dsk['percent'])} `{dsk['percent']:.1f}%` • `{dsk['used']:.1f}/{dsk['total']:.1f}GB`")
    
    # Сеть (без цветов, просто информация)
    lines.append(f"🌐 Net ↓`{net['recv']:.0f}MB` ↑`{net['sent']:.0f}MB`")

    # Сервисы
    if s.get("show_services", True):
        svcs = _flt_svc(monitor.get_running_services(), s)
        n    = s.get("max_services", 8)
        mode = {"all": "all", "filtered": "sys-off", "custom": "custom"}.get(
            s.get("services_mode", "filtered"), "")
        lines += ["", f"⚙️  SERVICES [{min(len(svcs), n)}/{len(svcs)}] _{mode}_"]
        lines += [f"  ✓ `{x['name']}`" for x in svcs[:n]]
        if len(svcs) > n:
            lines.append(f"  _…+{len(svcs) - n} более_")

    # Порты
    if s.get("show_ports", True):
        ports = _flt_ports(monitor.get_open_ports(), s)
        n     = s.get("max_ports", 12)
        lines += ["", f"🔌 PORTS [{len(ports)} открыто]"]
        lines += [f"  • `{p['port']}` {p['process']}" for p in ports[:n]]
        if len(ports) > n:
            lines.append(f"  _…+{len(ports) - n} ещё_")

    return "\n".join(lines)


def format_services(svcs, settings=None):
    """Список сервисов с эмодзи"""
    if settings:
        svcs = _flt_svc(svcs, settings)
    lines = [f"⚙️  SERVICES ({len(svcs)})", ""]
    lines += [f"  ✓ `{s['name']}`" for s in svcs] or ["  _none_"]
    return "\n".join(lines)


def format_ports(ports):
    """Список портов с эмодзи"""
    lines = [f"🔌 OPEN PORTS ({len(ports)})", ""]
    for p in ports:
        pid = f" pid:{p['pid']}" if p["pid"] else ""
        lines.append(f"  • `{p['port']}` ({p['address']}) {p['process']}{pid}")
    if not ports:
        lines.append("  _none_")
    return "\n".join(lines)


def format_ping(r):
    """Результат ping с эмодзи"""
    if r["success"]:
        if "avg" in r:
            return (
                f"🎯 *Ping `{r['host']}`*\n\n"
                f"✅ OK\n"
                f"min/avg/max: `{r['min']:.1f} / {r['avg']:.1f} / {r['max']:.1f} ms`"
            )
        return f"🎯 *Ping `{r['host']}`*\n\n✅ OK — хост доступен"
    return f"🎯 *Ping `{r['host']}`*\n\n❌ FAIL — {r.get('error', 'unreachable')}"


def format_daily_report(stats, date=None):
    """Ежедневный отчёт с эмодзи"""
    if not stats:
        return "📋 *Daily Report*\n\n📭 Нет данных"
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    recv = stats.get("net_recv_last", 0) - stats.get("net_recv_start", 0)
    sent = stats.get("net_sent_last", 0) - stats.get("net_sent_start", 0)
    return "\n".join([
        f"📋 *DAILY REPORT*  `{date}`",
        "",
        f"🟢 CPU  max {_bar(stats.get('cpu_max',  0))} `{stats.get('cpu_max',  0):.1f}%`",
        f"🟢 RAM  max {_bar(stats.get('ram_max',  0))} `{stats.get('ram_max',  0):.1f}%`",
        f"🟢 Disk max {_bar(stats.get('disk_max', 0))} `{stats.get('disk_max', 0):.1f}%`",
        f"🌐 Traffic ↓`{recv:.0f}MB` ↑`{sent:.0f}MB`",
    ])


def format_error(error_msg: str) -> str:
    """Форматирование ошибки"""
    return f"❌ *Error*\n\n`{error_msg}`"


def format_success(msg: str) -> str:
    """Форматирование успеха"""
    return f"✅ {msg}"


def format_warning(msg: str) -> str:
    """Форматирование предупреждения"""
    return f"⚠️  {msg}"


def format_alert(issues: list) -> str:
    """Форматирование критического алерта"""
    return "*🚨 ALERT — High Load*\n\n" + "\n".join(issues)


def format_reboot_notification() -> str:
    """Уведомление о перезагрузке"""
    return "🔄 Server rebooting. Back in ~1 min."
