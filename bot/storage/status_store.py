import json
import os
from datetime import datetime

DEFAULT_SETTINGS = {
    "services_blacklist": [
        "getty@tty1", "serial-getty@ttyS0", "ModemManager",
        "multipathd", "osconfig", "packagekit", "qemu-guest-agent",
    ],
    "services_filter":          [],
    "ports_filter":             [],
    "ports_blacklist":          [],
    "show_services":            True,
    "show_ports":               True,
    "services_mode":            "filtered",   # all | filtered | custom
    "max_services":             10,
    "max_ports":                15,
    "alerts_enabled":           False,
    "alert_cpu":                80,
    "alert_ram":                85,
    "alert_disk":               90,
    "daily_report_enabled":     False,
    "daily_report_time":        "09:00",
    "auto_reboot_enabled":      False,
    "auto_reboot_time":         "04:00",
}


class StatusStore:
    def __init__(self, filename="status_messages.json"):
        self.filename = filename
        self._data    = self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self):
        with open(self.filename, "w") as f:
            json.dump(self._data, f, indent=2)

    # ── channels ──────────────────────────────────────────────────────────────

    def add_channel(self, chat_id, msg_id):
        self._data.setdefault("channels", {})[str(chat_id)] = msg_id
        self._save()

    def get_channels(self):
        return {int(k): v for k, v in self._data.get("channels", {}).items()}

    def remove_channel(self, chat_id):
        self._data.get("channels", {}).pop(str(chat_id), None)
        self._save()

    # ── settings ──────────────────────────────────────────────────────────────

    def get_settings(self):
        s = DEFAULT_SETTINGS.copy()
        s.update(self._data.get("settings", {}))
        return s

    def update_settings(self, **kw):
        self._data.setdefault("settings", {}).update(kw)
        self._save()

    # ── stats ─────────────────────────────────────────────────────────────────

    def record_stats(self, cpu, ram, disk, recv, sent):
        today = datetime.now().strftime("%Y-%m-%d")
        self._data.setdefault("daily_stats", {})
        d = self._data["daily_stats"].get(today, {
            "cpu_max": 0, "ram_max": 0, "disk_max": 0,
            "net_recv_start": recv, "net_sent_start": sent,
            "net_recv_last":  recv, "net_sent_last":  sent,
        })
        d["cpu_max"]       = max(d["cpu_max"],  cpu)
        d["ram_max"]       = max(d["ram_max"],  ram)
        d["disk_max"]      = max(d["disk_max"], disk)
        d["net_recv_last"] = recv
        d["net_sent_last"] = sent
        self._data["daily_stats"][today] = d
        # keep last 7 days
        for k in sorted(self._data["daily_stats"])[:-7]:
            del self._data["daily_stats"][k]
        self._save()

    def get_daily_stats(self, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self._data.get("daily_stats", {}).get(date)
