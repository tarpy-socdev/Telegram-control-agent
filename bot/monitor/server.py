import psutil
import subprocess
import time
from datetime import datetime, timedelta


class ServerMonitor:
    _cpu_val  = 0.0
    _cpu_tick = 0.0

    def get_cpu_usage(self):
        now = time.monotonic()
        if now - self._cpu_tick > 2:
            ServerMonitor._cpu_val  = psutil.cpu_percent(interval=0)
            ServerMonitor._cpu_tick = now
        return self._cpu_val

    def get_memory_usage(self):
        m = psutil.virtual_memory()
        return {"total": m.total / 1024**3, "used": m.used / 1024**3, "percent": m.percent}

    def get_disk_usage(self, path="/"):
        d = psutil.disk_usage(path)
        return {"total": d.total / 1024**3, "used": d.used / 1024**3,
                "free": d.free / 1024**3, "percent": d.percent}

    def get_network_stats(self):
        n = psutil.net_io_counters()
        return {"recv": n.bytes_recv / 1024**2, "sent": n.bytes_sent / 1024**2}

    def get_load_average(self):
        try:
            l = psutil.getloadavg()
            return f"{l[0]:.2f} {l[1]:.2f} {l[2]:.2f}"
        except Exception:
            return "N/A"

    def get_uptime(self):
        try:
            delta = timedelta(seconds=int(datetime.now().timestamp() - psutil.boot_time()))
            d, rem = divmod(delta.total_seconds(), 86400)
            h, rem = divmod(rem, 3600)
            m, _   = divmod(rem, 60)
            parts  = []
            if d: parts.append(f"{int(d)}d")
            if h: parts.append(f"{int(h)}h")
            parts.append(f"{int(m)}m")
            return " ".join(parts)
        except Exception:
            return "N/A"

    def get_running_services(self):
        try:
            r = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--state=running",
                 "--no-pager", "--no-legend"],
                capture_output=True, text=True, timeout=10)
            return [{"name": l.split()[0].replace(".service", ""), "status": "running"}
                    for l in r.stdout.strip().splitlines() if l.split()]
        except Exception:
            return []

    def get_open_ports(self):
        try:
            seen, ports = set(), []
            for c in psutil.net_connections(kind="inet"):
                if c.status == "LISTEN" and c.laddr and c.laddr.port not in seen:
                    seen.add(c.laddr.port)
                    try:    proc = psutil.Process(c.pid).name() if c.pid else "?"
                    except: proc = "?"
                    ports.append({"port": c.laddr.port, "address": str(c.laddr.ip),
                                  "process": proc, "pid": c.pid})
            return sorted(ports, key=lambda x: x["port"])
        except Exception:
            return []

    def ping_host(self, host, count=4):
        try:
            r = subprocess.run(["ping", "-c", str(count), "-W", "3", host],
                               capture_output=True, text=True, timeout=20)
            if r.returncode != 0:
                return {"host": host, "success": False, "error": "Host unreachable"}
            for line in r.stdout.splitlines():
                if "min/avg/max" in line or "rtt" in line:
                    parts = line.split("=")[-1].strip().split("/")
                    if len(parts) >= 3:
                        return {"host": host, "success": True,
                                "min": float(parts[0]), "avg": float(parts[1]), "max": float(parts[2])}
            return {"host": host, "success": True}
        except Exception as e:
            return {"host": host, "success": False, "error": str(e)}

    def get_logs(self, service, lines=50):
        try:
            r = subprocess.run(["journalctl", "-u", service, "-n", str(lines), "--no-pager"],
                               capture_output=True, text=True, timeout=15)
            return r.stdout.strip() or f"No logs for {service}"
        except Exception as e:
            return str(e)
