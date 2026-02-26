# controller.py
# Работа с systemd, сервисами, логами

import subprocess

class SystemController:
    ALLOWED_SERVICES = [
        "xray",
        "nginx",
        "docker",
        "mtproto-proxy",
        "telegram-bot"
    ]

    def list_services(self):
        """Возвращает список разрешённых сервисов с их статусом"""
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--no-pager", "--no-legend"],
            capture_output=True, text=True
        )

        services = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            name = parts[0].replace(".service", "")
            state = parts[3]
            if name not in self.ALLOWED_SERVICES:
                continue
            services.append({"name": name, "active": state == "running"})
        return services

    def service_action(self, action, name):
        """Start/Stop/Restart сервис"""
        result = subprocess.run(["systemctl", action, name], capture_output=True, text=True)
        return result.returncode == 0

    def get_logs(self, service):
        """Возвращает последние 30 строк логов сервиса"""
        result = subprocess.run(
            ["journalctl", "-u", service, "-n", "30", "--no-pager"],
            capture_output=True, text=True
        )
        logs = result.stdout[-3500:]  # лимит Telegram
        return f"```\n{logs}\n```"
