#!/usr/bin/env python3
"""
setup_final.py — Полная установка Telegram Control Agent
Запускай: python3 setup_final.py
Содержит весь код внутри — ничего не качает.
"""
import os, sys, ast, subprocess, time

BOT_DIR      = "/opt/tg-control-agent"
SERVICE_NAME = "tg-control-agent"

# ─── КОНФИГ ───────────────────────────────────────────────────────────────────
BOT_TOKEN       = "YOUR_BOT_TOKEN_HERE"
ADMIN_IDS       = "YOUR_ADMIN_ID"
UPDATE_INTERVAL = "30"
# ──────────────────────────────────────────────────────────────────────────────

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[94m"; N = "\033[0m"
def ok(m):   print(f"{G}[OK]{N} {m}")
def err(m):  print(f"{R}[ERR]{N} {m}"); sys.exit(1)
def info(m): print(f"{B}[..]{N} {m}")
def warn(m): print(f"{Y}[!!]{N} {m}")

def run(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        err(f"Failed: {cmd}\n{r.stderr}")
    return r

# ─── BOT FILES ────────────────────────────────────────────────────────────────

def write(path, content):
    full = os.path.join(BOT_DIR, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if path.endswith(".py") and content.strip():
        try:
            ast.parse(content)
        except SyntaxError as e:
            err(f"Syntax error in {path}: {e}")
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    ok(path)


def write_all():

    write("bot/__init__.py", "")
    write("bot/core/__init__.py", "")
    write("bot/monitor/__init__.py", "")
    write("bot/storage/__init__.py", "")
    write("bot/telegram/__init__.py", "")

    # ── config ────────────────────────────────────────────────────────────────
    write("bot/config.py", (
        "import os\n"
        "from dotenv import load_dotenv\n"
        "load_dotenv()\n"
        "BOT_TOKEN = os.getenv('BOT_TOKEN', '')\n"
        "ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS','').split(',') if x.strip().isdigit()]\n"
        "UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '30'))\n"
    ))

    # ── monitor/server ────────────────────────────────────────────────────────
    write("bot/monitor/server.py", "\n".join([
        "import psutil, subprocess, time",
        "from datetime import datetime, timedelta",
        "",
        "class ServerMonitor:",
        "    _cpu_val  = 0.0",
        "    _cpu_tick = 0.0",
        "",
        "    def get_cpu_usage(self):",
        "        now = time.monotonic()",
        "        if now - self._cpu_tick > 2:",
        "            ServerMonitor._cpu_val  = psutil.cpu_percent(interval=0)",
        "            ServerMonitor._cpu_tick = now",
        "        return self._cpu_val",
        "",
        "    def get_memory_usage(self):",
        "        m = psutil.virtual_memory()",
        "        return {'total': m.total/1024**3, 'used': m.used/1024**3, 'percent': m.percent}",
        "",
        "    def get_disk_usage(self, path='/'):",
        "        d = psutil.disk_usage(path)",
        "        return {'total': d.total/1024**3, 'used': d.used/1024**3,",
        "                'free': d.free/1024**3, 'percent': d.percent}",
        "",
        "    def get_network_stats(self):",
        "        n = psutil.net_io_counters()",
        "        return {'recv': n.bytes_recv/1024**2, 'sent': n.bytes_sent/1024**2}",
        "",
        "    def get_load_average(self):",
        "        try:",
        "            l = psutil.getloadavg()",
        "            return f'{l[0]:.2f} {l[1]:.2f} {l[2]:.2f}'",
        "        except Exception:",
        "            return 'N/A'",
        "",
        "    def get_uptime(self):",
        "        try:",
        "            delta = timedelta(seconds=int(datetime.now().timestamp()-psutil.boot_time()))",
        "            d,rem = divmod(delta.total_seconds(), 86400)",
        "            h,rem = divmod(rem, 3600)",
        "            m,_   = divmod(rem, 60)",
        "            parts = []",
        "            if d: parts.append(f'{int(d)}d')",
        "            if h: parts.append(f'{int(h)}h')",
        "            parts.append(f'{int(m)}m')",
        "            return ' '.join(parts)",
        "        except Exception:",
        "            return 'N/A'",
        "",
        "    def get_running_services(self):",
        "        try:",
        "            r = subprocess.run(",
        "                ['systemctl','list-units','--type=service','--state=running',",
        "                 '--no-pager','--no-legend'],",
        "                capture_output=True, text=True, timeout=10)",
        "            return [{'name': l.split()[0].replace('.service',''), 'status':'running'}",
        "                    for l in r.stdout.strip().splitlines() if l.split()]",
        "        except Exception:",
        "            return []",
        "",
        "    def get_open_ports(self):",
        "        try:",
        "            seen, ports = set(), []",
        "            for c in psutil.net_connections(kind='inet'):",
        "                if c.status == 'LISTEN' and c.laddr and c.laddr.port not in seen:",
        "                    seen.add(c.laddr.port)",
        "                    try:    proc = psutil.Process(c.pid).name() if c.pid else '?'",
        "                    except: proc = '?'",
        "                    ports.append({'port':c.laddr.port, 'address':str(c.laddr.ip),",
        "                                  'process':proc, 'pid':c.pid})",
        "            return sorted(ports, key=lambda x: x['port'])",
        "        except Exception:",
        "            return []",
        "",
        "    def ping_host(self, host, count=4):",
        "        try:",
        "            r = subprocess.run(['ping','-c',str(count),'-W','3',host],",
        "                               capture_output=True, text=True, timeout=20)",
        "            if r.returncode != 0:",
        "                return {'host':host,'success':False,'error':'Host unreachable'}",
        "            for line in r.stdout.splitlines():",
        "                if 'min/avg/max' in line or 'rtt' in line:",
        "                    parts = line.split('=')[-1].strip().split('/')",
        "                    if len(parts) >= 3:",
        "                        return {'host':host,'success':True,",
        "                                'min':float(parts[0]),'avg':float(parts[1]),'max':float(parts[2])}",
        "            return {'host':host,'success':True}",
        "        except Exception as e:",
        "            return {'host':host,'success':False,'error':str(e)}",
        "",
        "    def get_logs(self, service, lines=50):",
        "        try:",
        "            r = subprocess.run(['journalctl','-u',service,'-n',str(lines),'--no-pager'],",
        "                               capture_output=True, text=True, timeout=15)",
        "            return r.stdout.strip() or f'No logs for {service}'",
        "        except Exception as e:",
        "            return str(e)",
    ]))

    # ── storage/status_store ──────────────────────────────────────────────────
    write("bot/storage/status_store.py", "\n".join([
        "import json, os",
        "from datetime import datetime",
        "",
        "DEFAULT_SETTINGS = {",
        "    'services_blacklist': ['getty@tty1','serial-getty@ttyS0','ModemManager',",
        "                           'multipathd','osconfig','packagekit','qemu-guest-agent'],",
        "    'services_filter':[], 'ports_filter':[], 'ports_blacklist':[],",
        "    'show_services':True, 'show_ports':True, 'services_mode':'filtered',",
        "    'max_services':10, 'max_ports':15,",
        "    'alerts_enabled':False, 'alert_cpu':80, 'alert_ram':85, 'alert_disk':90,",
        "    'daily_report_enabled':False, 'daily_report_time':'09:00',",
        "    'auto_reboot_enabled':False, 'auto_reboot_time':'04:00',",
        "}",
        "",
        "class StatusStore:",
        "    def __init__(self, filename='status_messages.json'):",
        "        self.filename = filename",
        "        self._data = self._load()",
        "",
        "    def _load(self):",
        "        if os.path.exists(self.filename):",
        "            try:",
        "                with open(self.filename) as f: return json.load(f)",
        "            except Exception: pass",
        "        return {}",
        "",
        "    def _save(self):",
        "        with open(self.filename, 'w') as f:",
        "            json.dump(self._data, f, indent=2)",
        "",
        "    def add_channel(self, chat_id, msg_id):",
        "        self._data.setdefault('channels', {})[str(chat_id)] = msg_id",
        "        self._save()",
        "",
        "    def get_channels(self):",
        "        return {int(k): v for k,v in self._data.get('channels',{}).items()}",
        "",
        "    def remove_channel(self, chat_id):",
        "        self._data.get('channels',{}).pop(str(chat_id), None)",
        "        self._save()",
        "",
        "    def get_settings(self):",
        "        s = DEFAULT_SETTINGS.copy()",
        "        s.update(self._data.get('settings', {}))",
        "        return s",
        "",
        "    def update_settings(self, **kw):",
        "        self._data.setdefault('settings', {}).update(kw)",
        "        self._save()",
        "",
        "    def record_stats(self, cpu, ram, disk, recv, sent):",
        "        today = datetime.now().strftime('%Y-%m-%d')",
        "        self._data.setdefault('daily_stats', {})",
        "        d = self._data['daily_stats'].get(today, {",
        "            'cpu_max':0,'ram_max':0,'disk_max':0,",
        "            'net_recv_start':recv,'net_sent_start':sent,",
        "            'net_recv_last':recv,'net_sent_last':sent,",
        "        })",
        "        d['cpu_max']       = max(d['cpu_max'], cpu)",
        "        d['ram_max']       = max(d['ram_max'], ram)",
        "        d['disk_max']      = max(d['disk_max'], disk)",
        "        d['net_recv_last'] = recv",
        "        d['net_sent_last'] = sent",
        "        self._data['daily_stats'][today] = d",
        "        for k in sorted(self._data['daily_stats'])[:-7]:",
        "            del self._data['daily_stats'][k]",
        "        self._save()",
        "",
        "    def get_daily_stats(self, date=None):",
        "        if date is None: date = datetime.now().strftime('%Y-%m-%d')",
        "        return self._data.get('daily_stats', {}).get(date)",
    ]))

    # ── core/controller ───────────────────────────────────────────────────────
    write("bot/core/controller.py", "\n".join([
        "import os, subprocess",
        "",
        "class SystemController:",
        "",
        "    @staticmethod",
        "    def service_action(action, name):",
        "        if action not in {'start','stop','restart','status'}:",
        "            return False, f'Invalid action: {action}'",
        "        try:",
        "            r = subprocess.run(['systemctl', action, name],",
        "                               capture_output=True, text=True, timeout=30)",
        "            return (True, f'{name}: {action} done') if r.returncode == 0 \\",
        "                   else (False, r.stderr.strip() or f'Error: {action} {name}')",
        "        except Exception as e:",
        "            return False, str(e)",
        "",
        "    @staticmethod",
        "    def ssh_disable():",
        "        try:",
        "            for u in ['ssh.socket','ssh']:",
        "                subprocess.run(['systemctl','stop',   u], timeout=10)",
        "                subprocess.run(['systemctl','disable',u], timeout=10)",
        "            return True, 'SSH stopped (service + socket)'",
        "        except Exception as e:",
        "            return False, str(e)",
        "",
        "    @staticmethod",
        "    def ssh_enable():",
        "        try:",
        "            for u in ['ssh.socket','ssh']:",
        "                subprocess.run(['systemctl','enable',u], timeout=10)",
        "            subprocess.run(['systemctl','start','ssh.socket'], timeout=10)",
        "            return True, 'SSH started (service + socket)'",
        "        except Exception as e:",
        "            return False, str(e)",
        "",
        "    @staticmethod",
        "    def get_autostart_services():",
        "        try:",
        "            r = subprocess.run(",
        "                ['systemctl','list-unit-files','--type=service',",
        "                 '--state=enabled','--no-pager','--no-legend'],",
        "                capture_output=True, text=True, timeout=15)",
        "            return [l.split()[0].replace('.service','')",
        "                    for l in r.stdout.strip().splitlines() if l.split()]",
        "        except Exception:",
        "            return []",
        "",
        "    @staticmethod",
        "    def reboot_server():",
        "        try:",
        "            subprocess.Popen(['bash','-c','sleep 5 && shutdown -r now'])",
        "            return True, 'ok'",
        "        except Exception as e:",
        "            return False, str(e)",
        "",
        "    @staticmethod",
        "    def clear_journal():",
        "        try:",
        "            r = subprocess.run(['journalctl','--vacuum-time=1d'],",
        "                               capture_output=True, text=True, timeout=60)",
        "            return True, r.stdout.strip() or 'Logs cleared'",
        "        except Exception as e:",
        "            return False, str(e)",
        "",
        "    @staticmethod",
        "    def close_port(port):",
        "        try:",
        "            r = subprocess.run(['lsof','-ti',f':{port}'],",
        "                               capture_output=True, text=True, timeout=10)",
        "            pids = [p for p in r.stdout.strip().splitlines() if p]",
        "            if not pids: return False, f'Port {port} not in use'",
        "            for pid in pids: subprocess.run(['kill','-9',pid], timeout=5)",
        "            return True, f'Port {port} closed ({len(pids)} processes)'",
        "        except Exception as e:",
        "            return False, str(e)",
        "",
        "    @staticmethod",
        "    def add_ssh_key(pubkey, username='root'):",
        "        try:",
        "            import pwd",
        "            try:",
        "                pw = pwd.getpwnam(username)",
        "                home, uid, gid = pw.pw_dir, pw.pw_uid, pw.pw_gid",
        "            except KeyError:",
        "                home, uid, gid = '/root', 0, 0",
        "            ssh_dir   = home + '/.ssh'",
        "            auth_file = ssh_dir + '/authorized_keys'",
        "            os.makedirs(ssh_dir, mode=0o700, exist_ok=True)",
        "            os.chown(ssh_dir, uid, gid)",
        "            existing = open(auth_file).read() if os.path.exists(auth_file) else ''",
        "            if pubkey.strip() in existing:",
        "                return False, 'Key already exists'",
        "            with open(auth_file, 'a') as f:",
        "                f.write('\\n' + pubkey.strip() + '\\n')",
        "            os.chmod(auth_file, 0o600)",
        "            os.chown(auth_file, uid, gid)",
        "            return True, f'SSH key added for {username}'",
        "        except Exception as e:",
        "            return False, str(e)",
    ]))

    # ── telegram/keyboards ────────────────────────────────────────────────────
    write("bot/telegram/keyboards.py", "\n".join([
        "from telegram import InlineKeyboardButton as B, InlineKeyboardMarkup as M",
        "",
        "def kb(rows): return M(rows)",
        "def b(text, cb): return B(text, callback_data=cb)",
        "",
        "def main_menu_keyboard():",
        "    return kb([",
        "        [b('Refresh','cmd:refresh')],",
        "        [b('Services','cmd:services'), b('Ports','cmd:ports')],",
        "        [b('Ping','cmd:ping_prompt'),  b('Logs','cmd:logs_prompt')],",
        "        [b('Restart svc','cmd:restart_prompt'), b('Stop svc','cmd:stop_prompt')],",
        "        [b('SSH','cmd:ssh_menu'), b('Security','cmd:security')],",
        "        [b('Settings','cmd:settings'), b('Reboot','cmd:reboot')],",
        "    ])",
        "",
        "def services_keyboard(mode):",
        "    opts = [('All','all'),('No-sys','filtered'),('Custom','custom')]",
        "    row  = [b(f'[{l}]' if mode==k else l, f'svcmode:{k}') for l,k in opts]",
        "    return kb([row, [b('Autostart','cmd:autostart')], [b('<< Home','cmd:home')]])",
        "",
        "def settings_keyboard(s):",
        "    t = lambda f,on,off: on if f else off",
        "    return kb([",
        "        [b(t(s['show_services'],'Svcs ON','Svcs OFF'),'settings:toggle_services'),",
        "         b(t(s['show_ports'],'Ports ON','Ports OFF'),'settings:toggle_ports')],",
        "        [b('Send status to channels','settings:send_status')],",
        "        [b('Link this chat','settings:add_channel'),",
        "         b('Unlink chat','settings:remove_channel')],",
        "        [b('Link channel by ID','settings:add_by_id')],",
        "        [b(t(s['alerts_enabled'],'Alerts ON','Alerts OFF'),'settings:toggle_alerts')],",
        "        [b(t(s['daily_report_enabled'],'Report ON','Report OFF'),'settings:toggle_report')],",
        "        [b(t(s['auto_reboot_enabled'],'AutoReboot ON','AutoReboot OFF'),'settings:toggle_reboot')],",
        "        [b('Hidden services','settings:blacklist_info')],",
        "        [b('<< Home','cmd:home')],",
        "    ])",
        "",
        "def ssh_keyboard(active):",
        "    return kb([",
        "        [b('Stop SSH' if active else 'Start SSH', 'ssh:stop' if active else 'ssh:start')],",
        "        [b('Add SSH key','ssh:add_key')],",
        "        [b('Key guide','ssh:keygen_info')],",
        "        [b('<< Home','cmd:home')],",
        "    ])",
        "",
        "def security_keyboard():",
        "    return kb([[b('SSH','cmd:ssh_menu')],[b('Close port','cmd:close_port_prompt')],",
        "               [b('Open ports','cmd:ports')],[b('<< Home','cmd:home')]])",
        "",
        "def confirm_keyboard(yes_cb, danger=False):",
        "    return kb([[b('!! YES !!' if danger else 'Yes', yes_cb), b('Cancel','cancel')]])",
        "",
        "def back_home():",
        "    return kb([[b('<< Home','cmd:home')]])",
        "",
        "def clear_logs_keyboard():",
        "    return kb([[b('Clear journalctl','clear_journalctl'), b('Cancel','cancel')]])",
    ]))

    # ── telegram/formatter ────────────────────────────────────────────────────
    write("bot/telegram/formatter.py", "\n".join([
        "from datetime import datetime",
        "",
        "def _ei(p): return '[G]' if p < 60 else ('[Y]' if p < 80 else '[R]')",
        "",
        "def _flt_svc(svcs, s):",
        "    mode = s.get('services_mode','filtered')",
        "    if mode == 'all': return svcs",
        "    if mode == 'custom':",
        "        wl = set(s.get('services_filter',[]))",
        "        return [x for x in svcs if x['name'] in wl]",
        "    bl = set(s.get('services_blacklist',[]))",
        "    return [x for x in svcs if x['name'] not in bl]",
        "",
        "def _flt_ports(ports, s):",
        "    bl = set(s.get('ports_blacklist',[]))",
        "    wl = s.get('ports_filter',[])",
        "    return [p for p in ports if p['port'] in wl] if wl else [p for p in ports if p['port'] not in bl]",
        "",
        "def format_status(monitor, settings=None):",
        "    s   = settings or {}",
        "    cpu = max(0.0, monitor.get_cpu_usage())",
        "    mem = monitor.get_memory_usage()",
        "    dsk = monitor.get_disk_usage()",
        "    net = monitor.get_network_stats()",
        "    lines = [",
        "        '*SERVER STATUS*',",
        "        f'`{datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}`  uptime: `{monitor.get_uptime()}`',",
        "        '',",
        "        f'CPU  {_ei(cpu)} `{cpu:.1f}%`   load: `{monitor.get_load_average()}`',",
        "        f'RAM  {_ei(mem[\"percent\"])} `{mem[\"percent\"]:.1f}%`  {mem[\"used\"]:.1f}/{mem[\"total\"]:.1f} GB',",
        "        f'Disk {_ei(dsk[\"percent\"])} `{dsk[\"percent\"]:.1f}%`  {dsk[\"used\"]:.1f}/{dsk[\"total\"]:.1f} GB',",
        "        f'Net  down `{net[\"recv\"]:.1f}MB`  up `{net[\"sent\"]:.1f}MB`',",
        "    ]",
        "    if s.get('show_services', True):",
        "        svcs = _flt_svc(monitor.get_running_services(), s)",
        "        n    = s.get('max_services', 10)",
        "        mode = {'all':'all','filtered':'no-sys','custom':'custom'}.get(s.get('services_mode','filtered'),'')",
        "        lines += ['', f'*SERVICES* {min(len(svcs),n)}/{len(svcs)} _{mode}_']",
        "        lines += [f'+ `{x[\"name\"]}`' for x in svcs[:n]]",
        "        if len(svcs) > n: lines.append(f'_+{len(svcs)-n} more_')",
        "    if s.get('show_ports', True):",
        "        ports = _flt_ports(monitor.get_open_ports(), s)",
        "        n     = s.get('max_ports', 15)",
        "        lines += ['', f'*PORTS* {len(ports)}']",
        "        lines += [f'- `{p[\"port\"]}` {p[\"process\"]}' for p in ports[:n]]",
        "        if len(ports) > n: lines.append(f'_+{len(ports)-n} more_')",
        "    return '\\n'.join(lines)",
        "",
        "def format_services(svcs, settings=None):",
        "    if settings: svcs = _flt_svc(svcs, settings)",
        "    lines = [f'*SERVICES* ({len(svcs)})', '']",
        "    lines += [f'+ `{s[\"name\"]}`' for s in svcs] or ['_none_']",
        "    return '\\n'.join(lines)",
        "",
        "def format_ports(ports):",
        "    lines = [f'*PORTS* ({len(ports)})', '']",
        "    lines += [f'- `{p[\"port\"]}` ({p[\"address\"]}) {p[\"process\"]}' for p in ports] or ['_none_']",
        "    return '\\n'.join(lines)",
        "",
        "def format_ping(r):",
        "    if r['success']:",
        "        if 'avg' in r:",
        "            return f'*Ping {r[\"host\"]}*\\n\\nOK  min/avg/max: `{r[\"min\"]:.1f}/{r[\"avg\"]:.1f}/{r[\"max\"]:.1f}ms`'",
        "        return f'*Ping {r[\"host\"]}*\\n\\nOK'",
        "    return f'*Ping {r[\"host\"]}*\\n\\nFAIL: {r.get(\"error\",\"unreachable\")}'",
        "",
        "def format_daily_report(stats, date=None):",
        "    if not stats: return '*Daily Report*\\n\\nNo data yet.'",
        "    if date is None: date = datetime.now().strftime('%Y-%m-%d')",
        "    recv = stats.get('net_recv_last',0) - stats.get('net_recv_start',0)",
        "    sent = stats.get('net_sent_last',0) - stats.get('net_sent_start',0)",
        "    return '\\n'.join([",
        "        f'*DAILY REPORT* `{date}`', '',",
        "        f'CPU max:  `{stats.get(\"cpu_max\",0):.1f}%`',",
        "        f'RAM max:  `{stats.get(\"ram_max\",0):.1f}%`',",
        "        f'Disk max: `{stats.get(\"disk_max\",0):.1f}%`',",
        "        f'Traffic:  down `{recv:.1f}MB`  up `{sent:.1f}MB`',",
        "    ])",
    ]))

    # ── telegram/handlers ─────────────────────────────────────────────────────
    # Written as a proper Python source file (not embedded string)
    handlers_code = (
        "import os\n"
        "from datetime import datetime\n"
        "from telegram import Update\n"
        "from telegram.ext import (\n"
        "    Application, CallbackQueryHandler, CommandHandler,\n"
        "    ContextTypes, MessageHandler, filters,\n"
        ")\n"
        "from bot.config import ADMIN_IDS\n"
        "from bot.core.controller import SystemController\n"
        "from bot.monitor.server import ServerMonitor\n"
        "from bot.storage.status_store import StatusStore\n"
        "from bot.telegram.formatter import (\n"
        "    format_daily_report, format_ping, format_ports, format_services, format_status,\n"
        ")\n"
        "from bot.telegram.keyboards import (\n"
        "    back_home, clear_logs_keyboard, confirm_keyboard,\n"
        "    main_menu_keyboard, security_keyboard, services_keyboard,\n"
        "    settings_keyboard, ssh_keyboard,\n"
        ")\n"
        "\n"
        "BOT_SVC = 'tg-control-agent'\n"
        "\n"
        "def _admin(uid): return not ADMIN_IDS or uid in ADMIN_IDS\n"
        "def _g(ctx, k):  return ctx.bot_data[k]\n"
        "\n"
        "async def _no_access(update):\n"
        "    m = update.message or (update.callback_query.message if update.callback_query else None)\n"
        "    if m: await m.reply_text('No access')\n"
        "\n"
        "async def _home(update, context):\n"
        "    mon = _g(context, 'monitor'); sto = _g(context, 'store')\n"
        "    text = format_status(mon, sto.get_settings())\n"
        "    kb   = main_menu_keyboard()\n"
        "    if update.callback_query:\n"
        "        try:\n"
        "            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=kb)\n"
        "            return\n"
        "        except Exception: pass\n"
        "    await context.bot.send_message(update.effective_chat.id, text, parse_mode='Markdown', reply_markup=kb)\n"
        "\n"
        "async def cmd_start(u,c):  await _home(u,c)\n"
        "async def cmd_status(u,c): await _home(u,c)\n"
        "async def cmd_menu(u,c):   await _home(u,c)\n"
        "\n"
        "async def cmd_ping(update, context):\n"
        "    if not context.args:\n"
        "        await update.message.reply_text('Usage: `/ping <host>`', parse_mode='Markdown'); return\n"
        "    host = context.args[0]\n"
        "    await update.message.reply_text(f'Pinging `{host}`...', parse_mode='Markdown')\n"
        "    await update.message.reply_text(\n"
        "        format_ping(_g(context,'monitor').ping_host(host)), parse_mode='Markdown', reply_markup=back_home())\n"
        "\n"
        "async def cmd_services(update, context):\n"
        "    sto = _g(context,'store'); s = sto.get_settings()\n"
        "    await update.message.reply_text(\n"
        "        format_services(_g(context,'monitor').get_running_services(), s),\n"
        "        parse_mode='Markdown', reply_markup=services_keyboard(s['services_mode']))\n"
        "\n"
        "async def cmd_ports(update, context):\n"
        "    await update.message.reply_text(\n"
        "        format_ports(_g(context,'monitor').get_open_ports()),\n"
        "        parse_mode='Markdown', reply_markup=back_home())\n"
        "\n"
        "async def _confirm(update, cb, msg, danger=False):\n"
        "    await update.message.reply_text(msg, reply_markup=confirm_keyboard(cb, danger), parse_mode='Markdown')\n"
        "\n"
        "async def cmd_restart_service(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not context.args:\n"
        "        await update.message.reply_text('Usage: `/restart_service <n>`', parse_mode='Markdown'); return\n"
        "    name = context.args[0]\n"
        "    warn = '\\n\\n*WARNING: bot service!*' if name == BOT_SVC else ''\n"
        "    await _confirm(update, f'restart_service:{name}', f'Restart `{name}`?{warn}', danger=bool(warn))\n"
        "\n"
        "async def cmd_stop_service(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not context.args:\n"
        "        await update.message.reply_text('Usage: `/stop_service <n>`', parse_mode='Markdown'); return\n"
        "    name = context.args[0]\n"
        "    warn = '\\n\\n*WARNING: bot will stop!*' if name == BOT_SVC else ''\n"
        "    await _confirm(update, f'stop_service:{name}', f'Stop `{name}`?{warn}', danger=bool(warn))\n"
        "\n"
        "async def cmd_reboot(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    await _confirm(update, 'reboot_server', 'Reboot server?', danger=True)\n"
        "\n"
        "async def cmd_logs(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not context.args:\n"
        "        await update.message.reply_text('Usage: `/logs <service> [lines]`', parse_mode='Markdown'); return\n"
        "    svc   = context.args[0]\n"
        "    lines = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 50\n"
        "    logs  = _g(context,'monitor').get_logs(svc, lines)\n"
        "    if len(logs) > 3800: logs = logs[-3800:]\n"
        "    await update.message.reply_text(f'*Logs {svc}:*\\n```\\n{logs}\\n```', parse_mode='Markdown', reply_markup=back_home())\n"
        "\n"
        "async def cmd_close_port(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not context.args or not context.args[0].isdigit():\n"
        "        await update.message.reply_text('Usage: `/close_port <port>`', parse_mode='Markdown'); return\n"
        "    await _confirm(update, f'close_port:{context.args[0]}', f'Close port `{context.args[0]}`?', danger=True)\n"
        "\n"
        "async def cmd_link_channel(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not context.args:\n"
        "        await update.message.reply_text(\n"
        "            'Usage: `/link_channel <id>`\\n\\nGet ID: forward a post from channel to @userinfobot',\n"
        "            parse_mode='Markdown'); return\n"
        "    try: cid = int(context.args[0])\n"
        "    except ValueError:\n"
        "        await update.message.reply_text('Invalid ID. Example: `-1001234567890`', parse_mode='Markdown'); return\n"
        "    sto = _g(context,'store')\n"
        "    try:\n"
        "        sent = await context.bot.send_message(cid, format_status(_g(context,'monitor'), sto.get_settings()), parse_mode='Markdown')\n"
        "        sto.add_channel(cid, sent.message_id)\n"
        "        await update.message.reply_text(f'Channel `{cid}` linked!', parse_mode='Markdown')\n"
        "    except Exception as e:\n"
        "        await update.message.reply_text(f'Failed: `{e}`\\nBot must be admin with post permission.', parse_mode='Markdown')\n"
        "\n"
        "async def cmd_broadcast(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not context.args:\n"
        "        await update.message.reply_text('Usage: `/broadcast <text>`', parse_mode='Markdown'); return\n"
        "    text = ' '.join(context.args)\n"
        "    channels = _g(context,'store').get_channels()\n"
        "    if not channels: await update.message.reply_text('No linked channels'); return\n"
        "    ok = 0\n"
        "    for cid in channels:\n"
        "        try: await context.bot.send_message(cid, f'[broadcast] {text}'); ok += 1\n"
        "        except Exception as e: print(f'broadcast {cid}: {e}')\n"
        "    await update.message.reply_text(f'Sent to {ok} chat(s)')\n"
        "\n"
        "async def cmd_report(update, context):\n"
        "    sto = _g(context,'store')\n"
        "    await update.message.reply_text(\n"
        "        format_daily_report(sto.get_daily_stats()), parse_mode='Markdown', reply_markup=back_home())\n"
        "\n"
        "async def cmd_set_report_time(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not context.args:\n"
        "        await update.message.reply_text('Usage: `/set_report_time 09:00`', parse_mode='Markdown'); return\n"
        "    _g(context,'store').update_settings(daily_report_time=context.args[0])\n"
        "    await update.message.reply_text(f'Report time: `{context.args[0]}`', parse_mode='Markdown')\n"
        "\n"
        "async def cmd_set_reboot_time(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not context.args:\n"
        "        await update.message.reply_text('Usage: `/set_reboot_time 04:00`', parse_mode='Markdown'); return\n"
        "    _g(context,'store').update_settings(auto_reboot_time=context.args[0])\n"
        "    await update.message.reply_text(f'Auto-reboot: `{context.args[0]}`', parse_mode='Markdown')\n"
        "\n"
        "async def cmd_set_alerts(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if len(context.args) < 3:\n"
        "        await update.message.reply_text('Usage: `/set_alerts <cpu> <ram> <disk>`', parse_mode='Markdown'); return\n"
        "    cpu, ram, disk = int(context.args[0]), int(context.args[1]), int(context.args[2])\n"
        "    _g(context,'store').update_settings(alert_cpu=cpu, alert_ram=ram, alert_disk=disk)\n"
        "    await update.message.reply_text(f'Thresholds: CPU>{cpu}% RAM>{ram}% Disk>{disk}%', parse_mode='Markdown')\n"
        "\n"
        "async def cmd_add_ssh_key(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not context.args:\n"
        "        await update.message.reply_text(\n"
        "            '*Add SSH key*\\n\\n'\n"
        "            'Usage: `/add_ssh_key <pubkey>`\\n'\n"
        "            'Specific user: `/add_ssh_key <pubkey> --user tarpy`\\n\\n'\n"
        "            'Generate:\\n```\\nssh-keygen -t ed25519\\ncat ~/.ssh/id_ed25519.pub\\n```',\n"
        "            parse_mode='Markdown'); return\n"
        "    args = list(context.args); username = 'root'\n"
        "    if '--user' in args:\n"
        "        i = args.index('--user')\n"
        "        if i + 1 < len(args):\n"
        "            username = args[i+1]\n"
        "            args = [a for j,a in enumerate(args) if j != i and j != i+1]\n"
        "    pubkey = ' '.join(args)\n"
        "    if not (pubkey.startswith('ssh-') or pubkey.startswith('ecdsa-')):\n"
        "        await update.message.reply_text('Invalid key (must start with ssh- or ecdsa-)', parse_mode='Markdown'); return\n"
        "    ok2, msg = _g(context,'controller').add_ssh_key(pubkey, username)\n"
        "    await update.message.reply_text(f'{'OK' if ok2 else 'FAIL'} {msg}', reply_markup=back_home())\n"
        "\n"
        "async def cmd_upload_file(update, context):\n"
        "    if not _admin(update.effective_user.id): await _no_access(update); return\n"
        "    if not update.message.document:\n"
        "        await update.message.reply_text('Send file as document. Saves to `/tmp/tg_uploads/`', parse_mode='Markdown'); return\n"
        "    doc  = update.message.document\n"
        "    dest = '/tmp/tg_uploads/' + doc.file_name\n"
        "    os.makedirs('/tmp/tg_uploads', exist_ok=True)\n"
        "    await update.message.reply_text(f'Downloading `{doc.file_name}`...', parse_mode='Markdown')\n"
        "    try:\n"
        "        f = await context.bot.get_file(doc.file_id)\n"
        "        await f.download_to_drive(dest)\n"
        "        await update.message.reply_text(f'Saved: `{dest}`  ({doc.file_size//1024} KB)', parse_mode='Markdown', reply_markup=back_home())\n"
        "    except Exception as e:\n"
        "        await update.message.reply_text(f'Error: `{e}`', parse_mode='Markdown')\n"
        "\n"
        "async def handle_callbacks(update, context):\n"
        "    q = update.callback_query; await q.answer()\n"
        "    d = q.data\n"
        "    ctl = _g(context,'controller'); mon = _g(context,'monitor'); sto = _g(context,'store')\n"
        "\n"
        "    async def edit(text, kb_=None, md=True):\n"
        "        try: await q.edit_message_text(text, parse_mode='Markdown' if md else None, reply_markup=kb_)\n"
        "        except Exception: pass\n"
        "\n"
        "    if d == 'cancel': await edit('Cancelled', md=False); return\n"
        "    if d == 'cmd:home': await _home(update, context); return\n"
        "    if d == 'cmd:refresh': await edit(format_status(mon, sto.get_settings()), main_menu_keyboard()); return\n"
        "\n"
        "    if d == 'cmd:services':\n"
        "        s = sto.get_settings()\n"
        "        await edit(format_services(mon.get_running_services(), s), services_keyboard(s['services_mode'])); return\n"
        "\n"
        "    if d == 'cmd:autostart':\n"
        "        svcs = ctl.get_autostart_services()\n"
        "        text = '*Autostart*\\n\\n' + '\\n'.join(f'+ `{s}`' for s in svcs) if svcs else 'None'\n"
        "        await edit(text, back_home()); return\n"
        "\n"
        "    if d.startswith('svcmode:'):\n"
        "        mode = d.split(':',1)[1]; sto.update_settings(services_mode=mode)\n"
        "        s = sto.get_settings()\n"
        "        await edit(format_services(mon.get_running_services(), s), services_keyboard(mode)); return\n"
        "\n"
        "    if d == 'cmd:ports': await edit(format_ports(mon.get_open_ports()), back_home()); return\n"
        "\n"
        "    TIPS = {\n"
        "        'cmd:ping_prompt':       'Type: `/ping google.com`',\n"
        "        'cmd:logs_prompt':       'Type: `/logs nginx 50`',\n"
        "        'cmd:restart_prompt':    'Type: `/restart_service nginx`',\n"
        "        'cmd:stop_prompt':       'Type: `/stop_service nginx`',\n"
        "        'cmd:close_port_prompt': 'Type: `/close_port 8080`',\n"
        "    }\n"
        "    if d in TIPS: await edit(TIPS[d], back_home()); return\n"
        "\n"
        "    if d == 'cmd:reboot': await edit('Reboot server?', confirm_keyboard('reboot_server', danger=True)); return\n"
        "\n"
        "    if d == 'cmd:settings':\n"
        "        s = sto.get_settings(); ch = sto.get_channels()\n"
        "        ids = '\\n'.join(f'  `{c}`' for c in ch) if ch else ''\n"
        "        await edit(f'*Settings*\\n\\nLinked: {len(ch)}\\n{ids}', settings_keyboard(s)); return\n"
        "\n"
        "    if d == 'cmd:ssh_menu':\n"
        "        import subprocess\n"
        "        active = subprocess.run(['systemctl','is-active','ssh'], capture_output=True, text=True).stdout.strip() == 'active'\n"
        "        await edit(f'*SSH*\\n\\nStatus: {\"active\" if active else \"stopped\"}', ssh_keyboard(active)); return\n"
        "\n"
        "    if d == 'cmd:security': await edit('*Security*', security_keyboard()); return\n"
        "\n"
        "    if d == 'ssh:start':\n"
        "        ok2, msg = ctl.ssh_enable()\n"
        "        await edit(f'{'OK' if ok2 else 'FAIL'} {msg}', back_home()); return\n"
        "\n"
        "    if d == 'ssh:stop':\n"
        "        await edit('Stop SSH?\\n\\nSSH access will be cut. Bot stays accessible.', confirm_keyboard('ssh:stop_confirm', danger=True)); return\n"
        "\n"
        "    if d == 'ssh:stop_confirm':\n"
        "        ok2, msg = ctl.ssh_disable()\n"
        "        await edit(f'{'OK' if ok2 else 'FAIL'} {msg}', back_home()); return\n"
        "\n"
        "    if d == 'ssh:add_key': await edit('Send:\\n`/add_ssh_key <pubkey>`\\nFor user:\\n`/add_ssh_key <pubkey> --user tarpy`', back_home()); return\n"
        "\n"
        "    if d == 'ssh:keygen_info':\n"
        "        await edit('*SSH Key Guide*\\n\\n1. Generate:\\n```\\nssh-keygen -t ed25519\\n```\\n2. Show:\\n```\\ncat ~/.ssh/id_ed25519.pub\\n```\\n3. Add:\\n`/add_ssh_key <content>`', back_home()); return\n"
        "\n"
        "    TOGGLES = {\n"
        "        'settings:toggle_services': 'show_services',\n"
        "        'settings:toggle_ports':    'show_ports',\n"
        "        'settings:toggle_alerts':   'alerts_enabled',\n"
        "        'settings:toggle_report':   'daily_report_enabled',\n"
        "        'settings:toggle_reboot':   'auto_reboot_enabled',\n"
        "    }\n"
        "    if d in TOGGLES:\n"
        "        key = TOGGLES[d]; s = sto.get_settings()\n"
        "        sto.update_settings(**{key: not s[key]})\n"
        "        await edit('*Settings*', settings_keyboard(sto.get_settings())); return\n"
        "\n"
        "    if d == 'settings:send_status':\n"
        "        channels = sto.get_channels()\n"
        "        if not channels: await edit('No linked channels. Use Link this chat or /link_channel', settings_keyboard(sto.get_settings())); return\n"
        "        text = format_status(mon, sto.get_settings())\n"
        "        ok_n, errors = 0, []\n"
        "        for cid in list(channels):\n"
        "            try:\n"
        "                sent = await context.bot.send_message(cid, text, parse_mode='Markdown')\n"
        "                sto.add_channel(cid, sent.message_id); ok_n += 1\n"
        "            except Exception as e: errors.append(f'`{cid}`: {e}')\n"
        "        result = f'Sent to {ok_n} chat(s)'\n"
        "        if errors: result += '\\nErrors:\\n' + '\\n'.join(errors)\n"
        "        await edit(result, settings_keyboard(sto.get_settings())); return\n"
        "\n"
        "    if d == 'settings:add_channel':\n"
        "        sent = await context.bot.send_message(q.message.chat_id, format_status(mon, sto.get_settings()), parse_mode='Markdown')\n"
        "        sto.add_channel(q.message.chat_id, sent.message_id)\n"
        "        await edit(f'Chat `{q.message.chat_id}` linked!', settings_keyboard(sto.get_settings())); return\n"
        "\n"
        "    if d == 'settings:add_by_id': await edit('1. Add bot as admin\\n2. Get ID via @userinfobot\\n3. Send: `/link_channel -1001234567890`', back_home()); return\n"
        "\n"
        "    if d == 'settings:remove_channel':\n"
        "        sto.remove_channel(q.message.chat_id)\n"
        "        await edit('Unlinked.', settings_keyboard(sto.get_settings())); return\n"
        "\n"
        "    if d == 'settings:blacklist_info':\n"
        "        bl = ', '.join(sto.get_settings()['services_blacklist']) or 'empty'\n"
        "        await edit(f'*Hidden:*\\n`{bl}`\\n\\nChange: `/set_blacklist s1,s2`', back_home()); return\n"
        "\n"
        "    if d.startswith('restart_service:'):\n"
        "        name = d.split(':',1)[1]; await edit(f'Restarting `{name}`...')\n"
        "        ok2, msg = ctl.service_action('restart', name)\n"
        "        await edit(f'{'OK' if ok2 else 'FAIL'} {msg}', back_home()); return\n"
        "\n"
        "    if d.startswith('stop_service:'):\n"
        "        name = d.split(':',1)[1]; await edit(f'Stopping `{name}`...')\n"
        "        ok2, msg = ctl.service_action('stop', name)\n"
        "        await edit(f'{'OK' if ok2 else 'FAIL'} {msg}', back_home()); return\n"
        "\n"
        "    if d == 'reboot_server':\n"
        "        ok2, _ = ctl.reboot_server()\n"
        "        if ok2:\n"
        "            for cid in sto.get_channels():\n"
        "                try: await context.bot.send_message(cid, 'Server rebooting. Back in ~1 min.')\n"
        "                except Exception: pass\n"
        "            await edit('Rebooting in 5 sec...')\n"
        "        else: await edit('Reboot failed')\n"
        "        return\n"
        "\n"
        "    if d == 'clear_journalctl':\n"
        "        await edit('Clearing...')\n"
        "        ok2, msg = ctl.clear_journal()\n"
        "        await edit(f'{'OK' if ok2 else 'FAIL'} {msg}', back_home()); return\n"
        "\n"
        "    if d.startswith('close_port:'):\n"
        "        port = int(d.split(':',1)[1]); await edit(f'Closing {port}...')\n"
        "        ok2, msg = ctl.close_port(port)\n"
        "        await edit(f'{'OK' if ok2 else 'FAIL'} {msg}', back_home()); return\n"
        "\n"
        "async def handle_new_member(update, context):\n"
        "    for m in update.message.new_chat_members:\n"
        "        if m.id == context.bot.id:\n"
        "            sto  = _g(context,'store')\n"
        "            text = format_status(_g(context,'monitor'), sto.get_settings())\n"
        "            sent = await context.bot.send_message(update.effective_chat.id, text, parse_mode='Markdown')\n"
        "            sto.add_channel(update.effective_chat.id, sent.message_id)\n"
        "            print(f'Auto-added to {update.effective_chat.id}')\n"
        "\n"
        "async def handle_document(update, context):\n"
        "    if _admin(update.effective_user.id): await cmd_upload_file(update, context)\n"
        "\n"
        "async def _push_status(context):\n"
        "    mon = _g(context,'monitor'); sto = _g(context,'store')\n"
        "    s   = sto.get_settings()\n"
        "    cpu = max(0.0, mon.get_cpu_usage())\n"
        "    mem = mon.get_memory_usage()\n"
        "    dsk = mon.get_disk_usage()\n"
        "    net = mon.get_network_stats()\n"
        "    sto.record_stats(cpu, mem['percent'], dsk['percent'], net['recv'], net['sent'])\n"
        "    text = format_status(mon, s)\n"
        "    for cid, mid in list(sto.get_channels().items()):\n"
        "        try:\n"
        "            await context.bot.edit_message_text(chat_id=cid, message_id=mid, text=text, parse_mode='Markdown')\n"
        "        except Exception as e:\n"
        "            if any(x in str(e).lower() for x in ['message to edit not found','can\\'t be edited','chat not found','bot was blocked']):\n"
        "                try:\n"
        "                    sent = await context.bot.send_message(cid, text, parse_mode='Markdown')\n"
        "                    sto.add_channel(cid, sent.message_id)\n"
        "                except Exception as e2: print(f'{cid}: {e2}')\n"
        "            else: print(f'{cid}: {e}')\n"
        "\n"
        "async def job_update_status(context): await _push_status(context)\n"
        "\n"
        "_alerted: set = set()\n"
        "\n"
        "async def job_alerts(context):\n"
        "    sto = _g(context,'store'); s = sto.get_settings()\n"
        "    if not s['alerts_enabled']: return\n"
        "    mon = _g(context,'monitor')\n"
        "    cpu = max(0.0, mon.get_cpu_usage())\n"
        "    mem = mon.get_memory_usage(); dsk = mon.get_disk_usage()\n"
        "    hits = []\n"
        "    if cpu            > s['alert_cpu']:  hits.append(f'CPU `{cpu:.1f}%` > {s[\"alert_cpu\"]}%')\n"
        "    if mem['percent'] > s['alert_ram']:  hits.append(f'RAM `{mem[\"percent\"]:.1f}%` > {s[\"alert_ram\"]}%')\n"
        "    if dsk['percent'] > s['alert_disk']: hits.append(f'Disk `{dsk[\"percent\"]:.1f}%` > {s[\"alert_disk\"]}%')\n"
        "    key = str(sorted(hits))\n"
        "    if not hits: _alerted.discard(key); return\n"
        "    if key in _alerted: return\n"
        "    _alerted.add(key)\n"
        "    text = '*ALERT*\\n\\n' + '\\n'.join(hits)\n"
        "    for cid in sto.get_channels():\n"
        "        try: await context.bot.send_message(cid, text, parse_mode='Markdown')\n"
        "        except Exception as e: print(f'alert {cid}: {e}')\n"
        "\n"
        "_report_at = _reboot_at = None\n"
        "\n"
        "async def job_daily_report(context):\n"
        "    global _report_at\n"
        "    sto = _g(context,'store'); s = sto.get_settings()\n"
        "    if not s['daily_report_enabled']: return\n"
        "    now = datetime.now().strftime('%H:%M')\n"
        "    if now != s['daily_report_time'] or _report_at == now: return\n"
        "    _report_at = now\n"
        "    text = format_daily_report(sto.get_daily_stats())\n"
        "    for cid in sto.get_channels():\n"
        "        try: await context.bot.send_message(cid, text, parse_mode='Markdown')\n"
        "        except Exception as e: print(f'report {cid}: {e}')\n"
        "\n"
        "async def job_auto_reboot(context):\n"
        "    global _reboot_at\n"
        "    sto = _g(context,'store'); s = sto.get_settings()\n"
        "    if not s['auto_reboot_enabled']: return\n"
        "    now = datetime.now().strftime('%H:%M')\n"
        "    if now != s['auto_reboot_time'] or _reboot_at == now: return\n"
        "    _reboot_at = now\n"
        "    for cid in sto.get_channels():\n"
        "        try: await context.bot.send_message(cid, f'Auto-reboot at {s[\"auto_reboot_time\"]}. Back soon.')\n"
        "        except Exception: pass\n"
        "    _g(context,'controller').reboot_server()\n"
        "\n"
        "async def job_on_startup(context):\n"
        "    sto = _g(context,'store')\n"
        "    if not sto.get_channels(): return\n"
        "    for cid in sto.get_channels():\n"
        "        try: await context.bot.send_message(cid, 'Bot online.')\n"
        "        except Exception as e: print(f'startup {cid}: {e}')\n"
        "\n"
        "def register_handlers(app):\n"
        "    for name, fn in [\n"
        "        ('start',cmd_start),('menu',cmd_menu),('status',cmd_status),\n"
        "        ('services',cmd_services),('ports',cmd_ports),('ping',cmd_ping),\n"
        "        ('restart_service',cmd_restart_service),('stop_service',cmd_stop_service),\n"
        "        ('reboot',cmd_reboot),('logs',cmd_logs),('close_port',cmd_close_port),\n"
        "        ('link_channel',cmd_link_channel),('broadcast',cmd_broadcast),\n"
        "        ('report',cmd_report),('set_report_time',cmd_set_report_time),\n"
        "        ('set_reboot_time',cmd_set_reboot_time),('set_alerts',cmd_set_alerts),\n"
        "        ('add_ssh_key',cmd_add_ssh_key),('upload',cmd_upload_file),\n"
        "    ]:\n"
        "        app.add_handler(CommandHandler(name, fn))\n"
        "    app.add_handler(CallbackQueryHandler(handle_callbacks))\n"
        "    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))\n"
        "    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))\n"
    )
    write("bot/telegram/handlers.py", handlers_code)

    # ── main ──────────────────────────────────────────────────────────────────
    write("bot/main.py", (
        "from telegram import Update\n"
        "from telegram.ext import Application\n"
        "from bot.config import BOT_TOKEN, UPDATE_INTERVAL\n"
        "from bot.core.controller import SystemController\n"
        "from bot.monitor.server import ServerMonitor\n"
        "from bot.storage.status_store import StatusStore\n"
        "from bot.telegram.handlers import (\n"
        "    job_alerts, job_auto_reboot, job_daily_report,\n"
        "    job_on_startup, job_update_status, register_handlers,\n"
        ")\n"
        "\n"
        "def main():\n"
        "    app = Application.builder().token(BOT_TOKEN).build()\n"
        "    app.bot_data.update({\n"
        "        'monitor':    ServerMonitor(),\n"
        "        'controller': SystemController(),\n"
        "        'store':      StatusStore(),\n"
        "    })\n"
        "    register_handlers(app)\n"
        "    jq = app.job_queue\n"
        "    jq.run_repeating(job_update_status, interval=UPDATE_INTERVAL, first=20)\n"
        "    jq.run_repeating(job_alerts,        interval=60, first=40)\n"
        "    jq.run_repeating(job_daily_report,  interval=60, first=60)\n"
        "    jq.run_repeating(job_auto_reboot,   interval=60, first=60)\n"
        "    jq.run_once(job_on_startup, when=12)\n"
        "    print(f'Bot started. Interval: {UPDATE_INTERVAL}s')\n"
        "    app.run_polling(allowed_updates=Update.ALL_TYPES)\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    ))


# ─── INSTALL.SH ──────────────────────────────────────────────────────────────

INSTALL_SH = r"""#!/usr/bin/env bash
set -euo pipefail
SVC="tg-control-agent"
DIR="/opt/tg-control-agent"
G='\033[0;32m' R='\033[0;31m' Y='\033[1;33m' N='\033[0m'
ok()   { echo -e "${G}[OK]${N} $1"; }
err()  { echo -e "${R}[ERR]${N} $1"; exit 1; }
info() { echo -e "${Y}[..]${N} $1"; }
need_root() { [ "$EUID" -eq 0 ] || err "Run as root"; }
case "${1:-help}" in
  install)
    need_root
    info "Installing packages..."
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv lsof curl
    info "Creating virtualenv..."
    python3 -m venv "$DIR/venv"
    "$DIR/venv/bin/pip" install -q "python-telegram-bot[job-queue]==20.7" psutil==5.9.6 python-dotenv==1.0.0
    info "Creating systemd service..."
    cat > "/etc/systemd/system/${SVC}.service" <<'SVC_EOF'
[Unit]
Description=Telegram Control Agent
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/opt/tg-control-agent
ExecStart=/opt/tg-control-agent/venv/bin/python -m bot.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
[Install]
WantedBy=multi-user.target
SVC_EOF
    systemctl daemon-reload
    systemctl enable "$SVC"
    ok "Install complete. Edit .env then: sudo ./install.sh start"
    ;;
  start)
    need_root; systemctl start "$SVC"; sleep 2
    systemctl is-active --quiet "$SVC" && ok "Started!" || err "Failed. Check: ./install.sh logs"
    ;;
  stop)
    need_root; systemctl stop "$SVC" && ok "Stopped"
    ;;
  restart)
    need_root; systemctl restart "$SVC"; sleep 2
    systemctl is-active --quiet "$SVC" && ok "Restarted!" || err "Failed"
    ;;
  status)   systemctl status "$SVC" --no-pager -l ;;
  logs)     journalctl -u "$SVC" -n "${2:-50}" --no-pager ;;
  logs-live) journalctl -u "$SVC" -f ;;
  *)
    echo "Usage: sudo ./install.sh {install|start|stop|restart|status|logs [N]|logs-live}"
    ;;
esac
"""

REQUIREMENTS = (
    "python-telegram-bot[job-queue]==20.7\n"
    "psutil==5.9.6\n"
    "python-dotenv==1.0.0\n"
)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Telegram Control Agent - Full Setup")
    print("=" * 55)
    print()

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        warn("BOT_TOKEN is not set!")
        warn(f"Edit this file and set BOT_TOKEN and ADMIN_IDS at the top.")
        sys.exit(1)

    info("Creating directories...")
    for d in [BOT_DIR, f"{BOT_DIR}/bot", f"{BOT_DIR}/bot/core",
              f"{BOT_DIR}/bot/monitor", f"{BOT_DIR}/bot/storage",
              f"{BOT_DIR}/bot/telegram"]:
        os.makedirs(d, exist_ok=True)
    ok("Directories ready")

    info("Writing bot files...")
    write_all()

    # .env
    env_path = os.path.join(BOT_DIR, ".env")
    with open(env_path, "w") as f:
        f.write(f"BOT_TOKEN={BOT_TOKEN}\nADMIN_IDS={ADMIN_IDS}\nUPDATE_INTERVAL={UPDATE_INTERVAL}\n")
    ok(".env")

    with open(os.path.join(BOT_DIR, ".env.example"), "w") as f:
        f.write("BOT_TOKEN=YOUR_BOT_TOKEN_HERE\nADMIN_IDS=YOUR_ADMIN_ID\nUPDATE_INTERVAL=30\n")
    ok(".env.example")

    with open(os.path.join(BOT_DIR, "requirements.txt"), "w") as f:
        f.write(REQUIREMENTS)
    ok("requirements.txt")

    install_path = os.path.join(BOT_DIR, "install.sh")
    with open(install_path, "w") as f:
        f.write(INSTALL_SH)
    os.chmod(install_path, 0o755)
    ok("install.sh")

    print()
    info("Installing system packages (python3, venv, lsof)...")
    run("apt-get update -qq && apt-get install -y -qq python3 python3-venv lsof curl", check=False)
    ok("System packages installed")

    info("Creating Python virtualenv...")
    run(f"python3 -m venv {BOT_DIR}/venv")
    ok("Virtualenv ready")

    info("Installing Python packages...")
    pip = f"{BOT_DIR}/venv/bin/pip"
    run(f'{pip} install -q "python-telegram-bot[job-queue]==20.7" psutil==5.9.6 python-dotenv==1.0.0')
    ok("Python packages installed")

    info("Configuring systemd...")
    svc_content = (
        "[Unit]\n"
        "Description=Telegram Control Agent\n"
        "After=network.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        "User=root\n"
        "WorkingDirectory=/opt/tg-control-agent\n"
        "ExecStart=/opt/tg-control-agent/venv/bin/python -m bot.main\n"
        "Restart=always\n"
        "RestartSec=10\n"
        "StandardOutput=journal\n"
        "StandardError=journal\n\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )
    with open(f"/etc/systemd/system/{SERVICE_NAME}.service", "w") as f:
        f.write(svc_content)
    run("systemctl daemon-reload")
    run(f"systemctl enable {SERVICE_NAME}")
    ok("Systemd service ready")

    info("Starting bot...")
    run(f"systemctl start {SERVICE_NAME}", check=False)
    time.sleep(3)
    r = run(f"systemctl is-active {SERVICE_NAME}", check=False)
    if r.stdout.strip() == "active":
        ok("Bot is running!")
    else:
        warn("Bot failed to start. Checking logs...")
        run(f"journalctl -u {SERVICE_NAME} -n 20 --no-pager", check=False)

    print()
    print("=" * 55)
    print("  Done!")
    print(f"  Bot token: {BOT_TOKEN[:12]}...")
    print(f"  Admin IDs: {ADMIN_IDS}")
    print(f"  Interval:  {UPDATE_INTERVAL}s")
    print()
    print("  Manage:")
    print(f"  cd {BOT_DIR}")
    print("  sudo ./install.sh logs 20")
    print("  sudo ./install.sh restart")
    print("=" * 55)


if __name__ == "__main__":
    main()
