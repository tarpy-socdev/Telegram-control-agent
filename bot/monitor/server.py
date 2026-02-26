# bot/monitor/server.py
# Мониторинг ресурсов сервера

import subprocess
from datetime import datetime
from typing import Any

import psutil


class ServerMonitor:

    @staticmethod
    def get_cpu_usage() -> float:
        return psutil.cpu_percent(interval=1)

    @staticmethod
    def get_load_average() -> str:
        try:
            load1, load5, load15 = psutil.getloadavg()
            cores = psutil.cpu_count()
            return f"{load1:.2f} {load5:.2f} {load15:.2f} (ядер: {cores})"
        except Exception:
            return "N/A"

    @staticmethod
    def get_memory_usage() -> dict[str, float]:
        mem = psutil.virtual_memory()
        return {
            "total": mem.total / (1024 ** 3),
            "used": mem.used / (1024 ** 3),
            "percent": mem.percent,
        }

    @staticmethod
    def get_disk_usage() -> dict[str, float]:
        disk = psutil.disk_usage("/")
        return {
            "total": disk.total / (1024 ** 3),
            "used": disk.used / (1024 ** 3),
            "free": disk.free / (1024 ** 3),
            "percent": disk.percent,
        }

    @staticmethod
    def get_network_stats() -> dict[str, float]:
        net = psutil.net_io_counters()
        return {
            "sent": net.bytes_sent / (1024 ** 2),
            "recv": net.bytes_recv / (1024 ** 2),
        }

    @staticmethod
    def get_uptime() -> str:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        delta = datetime.now() - boot_time
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{days}д {hours}ч {minutes}м"

    @staticmethod
    def get_running_services() -> list[dict[str, str]]:
        try:
            result = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--state=running",
                 "--no-pager", "--plain"],
                capture_output=True, text=True, timeout=10,
            )
            services = []
            for line in result.stdout.splitlines()[1:]:
                if ".service" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        services.append({
                            "name": parts[0].replace(".service", ""),
                            "status": parts[2],
                            "description": " ".join(parts[4:]) if len(parts) > 4 else "",
                        })
            return services[:20]
        except Exception as e:
            return [{"name": "error", "status": str(e), "description": ""}]

    @staticmethod
    def get_open_ports() -> list[dict[str, Any]]:
        try:
            connections = psutil.net_connections(kind="inet")
            ports: dict[int, dict] = {}
            for conn in connections:
                if conn.status == "LISTEN" and conn.laddr:
                    port = conn.laddr.port
                    if port not in ports:
                        try:
                            proc = psutil.Process(conn.pid) if conn.pid else None
                            name = proc.name() if proc else "unknown"
                        except Exception:
                            name = "unknown"
                        ports[port] = {
                            "port": port,
                            "address": conn.laddr.ip,
                            "process": name,
                            "pid": conn.pid,
                        }
            return sorted(ports.values(), key=lambda x: x["port"])
        except Exception as e:
            return [{"port": 0, "address": "error", "process": str(e), "pid": None}]

    @staticmethod
    def ping_host(host: str, count: int = 4) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["ping", "-c", str(count), host],
                capture_output=True, text=True, timeout=15,
            )
            output = result.stdout
            stats = [l for l in output.splitlines() if "min/avg/max" in l or "round-trip" in l]
            if stats:
                parts = stats[0].split("=")
                if len(parts) > 1:
                    values = parts[1].strip().split()[0].split("/")
                    return {
                        "success": True, "host": host,
                        "min": float(values[0]), "avg": float(values[1]),
                        "max": float(values[2]), "output": output,
                    }
            return {"success": result.returncode == 0, "host": host, "output": output}
        except Exception as e:
            return {"success": False, "host": host, "error": str(e)}

    @staticmethod
    def get_logs(service: str, lines: int = 50) -> str:
        try:
            result = subprocess.run(
                ["journalctl", "-u", service, "-n", str(lines), "--no-pager"],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Ошибка получения логов: {e}"
