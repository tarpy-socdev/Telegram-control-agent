from telegram import InlineKeyboardButton as B, InlineKeyboardMarkup as M


def kb(rows):        return M(rows)
def b(text, cb):     return B(text, callback_data=cb)


def main_menu_keyboard():
    return kb([
        [b("⟳ Refresh",       "cmd:refresh")],
        [b("⚙ Services",      "cmd:services"),   b("⬡ Ports",        "cmd:ports")],
        [b("◎ Ping",          "cmd:ping_prompt"), b("▤ Logs",         "cmd:logs_prompt")],
        [b("↺ Restart svc",   "cmd:restart_prompt"), b("■ Stop svc", "cmd:stop_prompt")],
        [b("⚿ SSH",           "cmd:ssh_menu"),    b("⛨ Security",    "cmd:security")],
        [b("≡ Settings",      "cmd:settings"),    b("↻ Reboot",       "cmd:reboot")],
    ])


def services_keyboard(mode):
    opts = [("All", "all"), ("No-sys", "filtered"), ("Custom", "custom")]
    row  = [b(f"[{l}]" if mode == k else l, f"svcmode:{k}") for l, k in opts]
    return kb([
        row,
        [b("▤ Autostart list", "cmd:autostart")],
        [b("← Home",           "cmd:home")],
    ])


def settings_keyboard(s):
    t = lambda f, on, off: on if f else off
    return kb([
        [b(t(s["show_services"], "Svcs ●", "Svcs ○"), "settings:toggle_services"),
         b(t(s["show_ports"],    "Ports ●", "Ports ○"), "settings:toggle_ports")],
        [b("↑ Send status to channels", "settings:send_status")],
        [b("+ Link this chat",  "settings:add_channel"),
         b("- Unlink chat",     "settings:remove_channel")],
        [b("⊕ Link channel by ID", "settings:add_by_id")],
        [b(t(s["alerts_enabled"],          "Alerts ●",     "Alerts ○"),     "settings:toggle_alerts")],
        [b(t(s["daily_report_enabled"],    "Report ●",     "Report ○"),     "settings:toggle_report")],
        [b(t(s["auto_reboot_enabled"],     "AutoReboot ●", "AutoReboot ○"), "settings:toggle_reboot")],
        [b("▤ Hidden services", "settings:blacklist_info")],
        [b("← Home",            "cmd:home")],
    ])


def ssh_keyboard(active):
    return kb([
        [b("■ Stop SSH" if active else "▶ Start SSH",
           "ssh:stop"   if active else "ssh:start")],
        [b("⊕ Add SSH key",    "ssh:add_key")],
        [b("? Key guide",      "ssh:keygen_info")],
        [b("← Home",           "cmd:home")],
    ])


def security_keyboard():
    return kb([
        [b("⚿ SSH",          "cmd:ssh_menu")],
        [b("✕ Close port",   "cmd:close_port_prompt")],
        [b("⬡ Open ports",   "cmd:ports")],
        [b("← Home",         "cmd:home")],
    ])


def confirm_keyboard(yes_cb, danger=False):
    return kb([[
        b("‼ YES ‼" if danger else "Yes", yes_cb),
        b("✕ Cancel", "cancel"),
    ]])


def back_home():
    return kb([[b("← Home", "cmd:home")]])


def clear_logs_keyboard():
    return kb([[b("Clear journalctl", "clear_journalctl"), b("✕ Cancel", "cancel")]])
