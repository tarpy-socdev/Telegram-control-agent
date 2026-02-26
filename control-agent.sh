#!/usr/bin/env python3
"""
Telegram Server Monitor (refactored version)

Главная идея:
1. Система собирает данные ОДИН раз
2. Telegram только читает готовые данные
3. Никаких тяжёлых systemctl при каждом /status
"""

import asyncio
import psutil
import json
import os
from datetime import datetime
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

BOT_TOKEN = "TOKEN"
UPDATE_INTERVAL = 30   # сбор данных каждые 30 сек
STATUS_FILE = "channels.json"


# =========================================================
# 1. SERVER MONITOR (работает только с системой)
# =========================================================
class ServerMonitor:
    """
    Этот класс ничего не знает про Telegram.
    Его задача — получить данные ОС.
    """

    def collect(self):
        """Собираем ВСЕ данные сразу"""

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu": psutil.cpu_percent(),
            "memory": {
                "percent": mem.percent,
                "used": round(mem.used / (1024**3), 2),
                "total": round(mem.total / (1024**3), 2),
            },
            "disk": {
                "percent": disk.percent,
                "used": round(disk.used / (1024**3), 2),
                "total": round(disk.total / (1024**3), 2),
            },
            "uptime": datetime.now().timestamp()
            - psutil.boot_time(),
        }


# =========================================================
# 2. DATA COLLECTOR (самая важная оптимизация)
# =========================================================
class DataCollector:
    """
    Фоновый сборщик данных.

    Раньше:
        каждая команда → system calls

    Теперь:
        background loop → cache
        команды читают cache
    """

    def __init__(self):
        self.monitor = ServerMonitor()
        self.cache = {}

    async def update_loop(self):
        """Бесконечный цикл обновления кеша"""
        while True:
            # psutil блокирующий → уносим в thread
            self.cache = await asyncio.to_thread(
                self.monitor.collect
            )
            await asyncio.sleep(UPDATE_INTERVAL)

    def get(self):
        """Telegram читает только это"""
        return self.cache


# =========================================================
# 3. CHANNEL MANAGER
# =========================================================
class ChannelManager:
    """
    Отвечает только за хранение каналов.
    Telegram логика сюда НЕ лезет.
    """

    def __init__(self, file):
        self.file = file
        self.channels = self.load()

    def load(self):
        if os.path.exists(self.file):
            return json.load(open(self.file))
        return {}

    def save(self):
        json.dump(self.channels, open(self.file, "w"), indent=2)

    def add(self, chat_id, message_id):
        self.channels[str(chat_id)] = message_id
        self.save()

    def all(self):
        return self.channels.items()


# =========================================================
# 4. MESSAGE BUILDER (отдельный слой отображения)
# =========================================================
def build_status(data: dict) -> str:
    """
    Только форматирование.
    НИКАКИХ system calls здесь быть не должно.
    """

    if not data:
        return "⏳ Сбор данных..."

    return f"""
🖥 СТАТУС СЕРВЕРА

CPU: {data['cpu']}%
RAM: {data['memory']['percent']}%
Disk: {data['disk']['percent']}%
"""


# =========================================================
# 5. TELEGRAM COMMANDS (UI слой)
# =========================================================
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram слой НЕ собирает данные.
    Он просто показывает cache.
    """

    collector: DataCollector = context.bot_data["collector"]
    data = collector.get()

    await update.message.reply_text(build_status(data))


# =========================================================
# 6. PERIODIC CHANNEL UPDATE
# =========================================================
async def update_channels(context: ContextTypes.DEFAULT_TYPE):
    collector = context.bot_data["collector"]
    manager: ChannelManager = context.bot_data["channels"]

    text = build_status(collector.get())

    for chat_id, msg_id in manager.all():
        try:
            await context.bot.edit_message_text(
                chat_id=int(chat_id),
                message_id=msg_id,
                text=text,
            )
        except Exception as e:
            print("update error:", e)


# =========================================================
# 7. MAIN
# =========================================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # создаём сервисы
    collector = DataCollector()
    channels = ChannelManager(STATUS_FILE)

    # кладём их в глобальный bot context
    app.bot_data["collector"] = collector
    app.bot_data["channels"] = channels

    # команды
    app.add_handler(CommandHandler("status", status_command))

    # запуск фонового сборщика
    asyncio.get_event_loop().create_task(
        collector.update_loop()
    )

    # автообновление каналов
    app.job_queue.run_repeating(update_channels, interval=60)

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
