#!/bin/bash

echo "======================================"
echo "Установка Telegram Server Monitor Bot"
echo "======================================"
echo ""

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Запустите скрипт с правами root (sudo ./install.sh)"
    exit 1
fi

# Устанавливаем зависимости
echo "📦 Устанавливаю зависимости..."
apt update
apt install -y python3 python3-pip lsof

# Устанавливаем Python библиотеки
echo "📦 Устанавливаю Python библиотеки..."
pip3 install -r requirements.txt --break-system-packages

# Создаем директорию
echo "📁 Создаю директорию..."
mkdir -p /opt/server-monitor-bot

# Копируем файлы
echo "📋 Копирую файлы..."
cp server_monitor_bot.py /opt/server-monitor-bot/
chmod +x /opt/server-monitor-bot/server_monitor_bot.py

# Устанавливаем systemd service
echo "⚙️ Настраиваю автозапуск..."
cp server-monitor-bot.service /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "✅ Установка завершена!"
echo ""
echo "======================================"
echo "📝 СЛЕДУЮЩИЕ ШАГИ:"
echo "======================================"
echo ""
echo "1. Создай бота в @BotFather и получи токен"
echo ""
echo "2. Отредактируй файл конфигурации:"
echo "   nano /opt/server-monitor-bot/server_monitor_bot.py"
echo ""
echo "   Измени:"
echo "   - BOT_TOKEN = \"твой_токен_сюда\""
echo "   - ADMIN_IDS = [твой_telegram_id]  # Узнай ID у @userinfobot"
echo ""
echo "3. Запусти бота:"
echo "   systemctl start server-monitor-bot"
echo "   systemctl enable server-monitor-bot"
echo ""
echo "4. Проверь статус:"
echo "   systemctl status server-monitor-bot"
echo ""
echo "5. Добавь бота в свой канал как администратора"
echo ""
echo "======================================"
echo ""
echo "📖 Логи бота: journalctl -u server-monitor-bot -f"
echo ""
