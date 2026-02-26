# bot/main.py
# Точка входа бота

from telegram import Update
from telegram.ext import Application

from bot.config import BOT_TOKEN, UPDATE_INTERVAL
from bot.core.controller import SystemController
from bot.monitor.server import ServerMonitor
from bot.storage.status_store import StatusStore
from bot.telegram.handlers import job_update_status, register_handlers


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    # Shared объекты — доступны из любого хендлера через context.bot_data
    application.bot_data["monitor"] = ServerMonitor()
    application.bot_data["controller"] = SystemController()
    application.bot_data["store"] = StatusStore()

    # Регистрируем все хендлеры
    register_handlers(application)

    # Периодическое обновление статуса в каналах
    application.job_queue.run_repeating(
        job_update_status,
        interval=UPDATE_INTERVAL,
        first=10,
    )

    print(f"🤖 Бот запущен! Обновление каждые {UPDATE_INTERVAL} сек.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
