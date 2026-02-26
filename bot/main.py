# main.py
# Точка входа бота

from telegram.ext import Application
from bot.core.controller import SystemController
from bot.telegram.handlers import register_handlers

from bot.config import BOT_TOKEN

def main():
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Создаём контроллер
    controller = SystemController()
    application.bot_data["controller"] = controller

    # Регистрируем все обработчики
    register_handlers(application)

    print("🤖 Бот запущен!")
    application.run_polling()


if __name__ == "__main__":
    main()
