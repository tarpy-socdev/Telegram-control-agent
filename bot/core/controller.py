# bot/core/controller.py
# Управление systemd сервисами

import subprocess


class SystemController:

    @staticmethod
    def service_action(action: str, name: str) -> tuple[bool, str]:
        """Выполнить действие над сервисом. Возвращает (успех, сообщение)."""
        allowed_actions = {"start", "stop", "restart", "status"}
        if action not in allowed_actions:
            return False, f"Недопустимое действие: {action}"

        try:
            result = subprocess.run(
                ["systemctl", action, name],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return True, f"✅ Сервис {name} успешно {action}"
            else:
                return False, result.stderr.strip() or f"Ошибка при {action} {name}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def reboot_server() -> tuple[bool, str]:
        """Перезагрузить сервер."""
        try:
            subprocess.Popen(["shutdown", "-r", "+0"])
            return True, "Сервер перезагружается..."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def clear_journal() -> tuple[bool, str]:
        """Очистить journalctl старше 1 дня."""
        try:
            result = subprocess.run(
                ["journalctl", "--vacuum-time=1d"],
                capture_output=True, text=True, timeout=60,
            )
            return True, result.stdout.strip() or "Логи очищены"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def close_port(port: int) -> tuple[bool, str]:
        """Завершить процессы на порту."""
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True, timeout=10,
            )
            pids = [p for p in result.stdout.strip().splitlines() if p]
            if not pids:
                return False, f"Порт {port} не используется"
            for pid in pids:
                subprocess.run(["kill", "-9", pid], timeout=5)
            return True, f"Порт {port} закрыт (завершено процессов: {len(pids)})"
        except Exception as e:
            return False, str(e)
