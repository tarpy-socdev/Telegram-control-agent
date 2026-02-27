from telegram import Update
from telegram.ext import Application

from bot.config import BOT_TOKEN, UPDATE_INTERVAL
from bot.core.controller import SystemController
from bot.monitor.server import ServerMonitor
from bot.storage.status_store import StatusStore
from bot.telegram.handlers import (
    job_alerts, job_auto_reboot, job_daily_report,
    job_on_startup, job_update_status, register_handlers,
)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data.update({
        "monitor":    ServerMonitor(),
        "controller": SystemController(),
        "store":      StatusStore(),
    })
    register_handlers(app)
    jq = app.job_queue
    jq.run_repeating(job_update_status, interval=UPDATE_INTERVAL, first=20)
    jq.run_repeating(job_alerts,        interval=60,  first=40)
    jq.run_repeating(job_daily_report,  interval=60,  first=60)
    jq.run_repeating(job_auto_reboot,   interval=60,  first=60)
    jq.run_once(job_on_startup, when=12)
    print(f"Bot started. Interval: {UPDATE_INTERVAL}s")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
