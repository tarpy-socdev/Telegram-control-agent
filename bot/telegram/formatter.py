from datetime import datetime

# Status indicators
def _dot(p):
    if p < 60:  return "●"   # green-ish
    if p < 80:  return "◕"   # yellow
    return "○"               # critical (inverted)

def _bar(p, width=8):
    """ASCII progress bar: [████░░░░]"""
    filled = round(p / 100 * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"

def _flt_svc(svcs, s):
    mode = s.get("services_mode", "filtered")
    if mode == "all":
        return svcs
    if mode == "custom":
        wl = set(s.get("services_filter", []))
        return [x for x in svcs if x["name"] in wl]
    bl = set(s.get("services_blacklist", []))
    return [x for x in svcs if x["name"] not in bl]

def _flt_ports(ports, s):
    bl = set(s.get("ports_blacklist", []))
    wl = s.get("ports_filter", [])
    if wl:
        return [p for p in ports if p["port"] in wl]
    return [p for p in ports if p["port"] not in bl]


def format_status(monitor, settings=None):
    s   = settings or {}
    cpu = max(0.0, monitor.get_cpu_usage())
    mem = monitor.get_memory_usage()
    dsk = monitor.get_disk_usage()
    net = monitor.get_network_stats()

    lines = [
        "*≡ SERVER STATUS*",
        f"`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  ⏱ `{monitor.get_uptime()}`",
        "",
        f"CPU  {_dot(cpu)} {_bar(cpu)} `{cpu:.1f}%`  load `{monitor.get_load_average()}`",
        f"RAM  {_dot(mem['percent'])} {_bar(mem['percent'])} `{mem['percent']:.1f}%`  {mem['used']:.1f}/{mem['total']:.1f} GB",
        f"Disk {_dot(dsk['percent'])} {_bar(dsk['percent'])} `{dsk['percent']:.1f}%`  {dsk['used']:.1f}/{dsk['total']:.1f} GB",
        f"Net  ↓ `{net['recv']:.1f}MB`  ↑ `{net['sent']:.1f}MB`",
    ]

    if s.get("show_services", True):
        svcs = _flt_svc(monitor.get_running_services(), s)
        n    = s.get("max_services", 10)
        mode = {"all": "all", "filtered": "no-sys", "custom": "custom"}.get(
            s.get("services_mode", "filtered"), "")
        lines += ["", f"*⚙ SERVICES*  {min(len(svcs), n)}/{len(svcs)}  _{mode}_"]
        lines += [f"  + `{x['name']}`" for x in svcs[:n]]
        if len(svcs) > n:
            lines.append(f"  _...+{len(svcs) - n} more_")

    if s.get("show_ports", True):
        ports = _flt_ports(monitor.get_open_ports(), s)
        n     = s.get("max_ports", 15)
        lines += ["", f"*⬡ PORTS*  {len(ports)}"]
        lines += [f"  - `{p['port']}` {p['process']}" for p in ports[:n]]
        if len(ports) > n:
            lines.append(f"  _...+{len(ports) - n} more_")

    return "\n".join(lines)


def format_services(svcs, settings=None):
    if settings:
        svcs = _flt_svc(svcs, settings)
    lines = [f"*⚙ SERVICES* ({len(svcs)})", ""]
    lines += [f"  + `{s['name']}`" for s in svcs] or ["  _none_"]
    return "\n".join(lines)


def format_ports(ports):
    lines = [f"*⬡ OPEN PORTS* ({len(ports)})", ""]
    for p in ports:
        pid = f" pid:{p['pid']}" if p["pid"] else ""
        lines.append(f"  - `{p['port']}` ({p['address']}) {p['process']}{pid}")
    if not ports:
        lines.append("  _none_")
    return "\n".join(lines)


def format_ping(r):
    if r["success"]:
        if "avg" in r:
            return (
                f"*◎ Ping `{r['host']}`*\n\n"
                f"✓ OK\n"
                f"min/avg/max: `{r['min']:.1f} / {r['avg']:.1f} / {r['max']:.1f} ms`"
            )
        return f"*◎ Ping `{r['host']}`*\n\n✓ OK — host reachable"
    return f"*◎ Ping `{r['host']}`*\n\n✕ FAIL — {r.get('error', 'unreachable')}"


def format_daily_report(stats, date=None):
    if not stats:
        return "*▤ Daily Report*\n\nNo data yet."
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    recv = stats.get("net_recv_last", 0) - stats.get("net_recv_start", 0)
    sent = stats.get("net_sent_last", 0) - stats.get("net_sent_start", 0)
    return "\n".join([
        f"*▤ DAILY REPORT*  `{date}`",
        "",
        f"CPU  max  {_bar(stats.get('cpu_max',  0))}  `{stats.get('cpu_max',  0):.1f}%`",
        f"RAM  max  {_bar(stats.get('ram_max',  0))}  `{stats.get('ram_max',  0):.1f}%`",
        f"Disk max  {_bar(stats.get('disk_max', 0))}  `{stats.get('disk_max', 0):.1f}%`",
        f"Traffic  ↓ `{recv:.1f}MB`  ↑ `{sent:.1f}MB`",
    ])
