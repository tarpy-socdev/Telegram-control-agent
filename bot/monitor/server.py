# server.py
# Мониторинг ресурсов сервера

import psutil
from datetime import datetime

class ServerMonitor:

    @staticmethod
    def get_cpu_usage():
        return psutil.cpu_percent(interval=1)

    @staticmethod
    def get_memory_usage():
        mem = psutil.virtual_memory()
        return {"total": mem.total, "used": mem.used, "percent": mem.percent}

    @staticmethod
    def get_disk_usage():
        disk = psutil.disk_usage('/')
        return {"total": disk.total, "used": disk.used, "free": disk.free, "percent": disk.percent}

    @staticmethod
    def get_uptime():
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        return f"{days}д {hours}ч {minutes}м"
