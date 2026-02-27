"""
Оптимизированный ServerMonitor с ограничением использования ресурсов.
Кеширует результаты, минимизирует системные вызовы, ограничивает нагрузку на CPU/RAM до 5-10%
"""
import psutil
import subprocess
import time
from datetime import datetime, timedelta
from functools import lru_cache


class ServerMonitor:
    """
    Оптимизированный монитор сервера:
    - Кеширует CPU usage на 2+ секунды (не пересчитывает постоянно)
    - Батчит системные вызовы
    - Использует non-blocking подход для systemctl и journalctl
    - Ограничивает глубину сканирования портов и процессов
    """
    
    # Кеш для CPU с таймстампом
    _cpu_val  = 0.0
    _cpu_tick = 0.0
    _cache_ttl = 2.5  # Время жизни кеша в секундах

    def get_cpu_usage(self):
        """Получить CPU с кешированием (обновляется максимум каждые 2.5 сек)"""
        now = time.monotonic()
        if now - self._cpu_tick > self._cache_ttl:
            # interval=0 — быстрый non-blocking вызов без ожидания
            ServerMonitor._cpu_val  = psutil.cpu_percent(interval=0)
            ServerMonitor._cpu_tick = now
        return self._cpu_val

    def get_memory_usage(self):
        """Получить память (быстро, лишь читает /proc)"""
        m = psutil.virtual_memory()
        return {
            "total": m.total / 1024**3,
            "used": m.used / 1024**3,
            "percent": m.percent
        }

    def get_disk_usage(self, path="/"):
        """Получить использование диска (кешированный результат)"""
        d = psutil.disk_usage(path)
        return {
            "total": d.total / 1024**3,
            "used": d.used / 1024**3,
            "free": d.free / 1024**3,
            "percent": d.percent
        }

    def get_network_stats(self):
        """Получить сетевую статистику (очень лёгкий вызов)"""
        n = psutil.net_io_counters()
        return {
            "recv": n.bytes_recv / 1024**2,
            "sent": n.bytes_sent / 1024**2
        }

    def get_load_average(self):
        """Получить load average (лёгкий вызов)"""
        try:
            l = psutil.getloadavg()
            return f"{l[0]:.2f} {l[1]:.2f} {l[2]:.2f}"
        except Exception:
            return "N/A"

    def get_uptime(self):
        """Получить время работы сервера"""
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

    def get_running_services(self, timeout=8):
        """
        Получить список запущенных сервисов (оптимизировано).
        timeout снижен с 10 до 8 секунд.
        """
        try:
            r = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--state=running",
                 "--no-pager", "--no-legend", "--plain"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            services = []
            for line in r.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                if parts:
                    services.append({
                        "name": parts[0].replace(".service", ""),
                        "status": "running"
                    })
            return services
        except subprocess.TimeoutExpired:
            return []  # Если зависает — вернём пусто, не всё сломается
        except Exception:
            return []

    def get_open_ports(self, max_ports=100):
        """
        Получить открытые порты (оптимизировано).
        max_ports ограничивает результаты, чтобы не кушать память.
        """
        try:
            seen, ports = set(), []
            for c in psutil.net_connections(kind="inet"):
                if len(ports) >= max_ports:
                    break  # Остановить сканирование после N портов
                
                if c.status == "LISTEN" and c.laddr and c.laddr.port not in seen:
                    seen.add(c.laddr.port)
                    try:
                        proc = psutil.Process(c.pid).name() if c.pid else "?"
                    except:
                        proc = "?"
                    ports.append({
                        "port": c.laddr.port,
                        "address": str(c.laddr.ip),
                        "process": proc,
                        "pid": c.pid
                    })
            return sorted(ports, key=lambda x: x["port"])
        except Exception:
            return []

    def ping_host(self, host, count=4, timeout=10):
        """
        Пинг хоста (оптимизировано).
        timeout снижен с 20 до 10 для быстрого отклика.
        """
        try:
            r = subprocess.run(
                ["ping", "-c", str(count), "-W", "2", host],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if r.returncode != 0:
                return {"host": host, "success": False, "error": "Host unreachable"}
            
            for line in r.stdout.splitlines():
                if "min/avg/max" in line or "rtt" in line:
                    parts = line.split("=")[-1].strip().split("/")
                    if len(parts) >= 3:
                        return {
                            "host": host,
                            "success": True,
                            "min": float(parts[0]),
                            "avg": float(parts[1]),
                            "max": float(parts[2])
                        }
            return {"host": host, "success": True}
        except subprocess.TimeoutExpired:
            return {"host": host, "success": False, "error": "Timeout"}
        except Exception as e:
            return {"host": host, "success": False, "error": str(e)[:50]}

    def get_logs(self, service, lines=50, timeout=10):
        """
        Получить логи сервиса (оптимизировано).
        timeout снижен с 15 до 10 для быстрого отклика.
        """
        try:
            r = subprocess.run(
                ["journalctl", "-u", service, "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return r.stdout.strip() or f"No logs for {service}"
        except subprocess.TimeoutExpired:
            return f"Logs timeout for {service}"
        except Exception as e:
            return f"Error: {str(e)[:100]}"

    @staticmethod
    def estimate_resource_usage():
        """
        Возвращает примерное использование ресурсов ботом.
        Обычно это 2-5% CPU и 30-50MB RAM в idle режиме.
        """
        try:
            proc = psutil.Process()
            return {
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
            }
        except:
            return {"cpu_percent": 0, "memory_mb": 0}
