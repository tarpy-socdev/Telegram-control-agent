#!/usr/bin/env python3
"""
Telegram Server Monitor Bot
Мониторит сервер и обновляет статус в канале каждые 5 минут
"""

import asyncio
import psutil
import socket
import subprocess
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Получи у @BotFather
ADMIN_IDS = []  # ID админов которые могут выполнять команды, например [123456789, 987654321]
UPDATE_INTERVAL = 300  # 5 минут в секундах

# Файл для хранения ID сообщений в каналах
STATUS_FILE = "status_messages.json"


class ServerMonitor:
    """Класс для мониторинга сервера"""
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Получить использование CPU"""
        return psutil.cpu_percent(interval=1)
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Получить использование памяти"""
        mem = psutil.virtual_memory()
        return {
            'total': mem.total / (1024**3),  # GB
            'used': mem.used / (1024**3),
            'percent': mem.percent
        }
    
    @staticmethod
    def get_disk_usage() -> Dict[str, float]:
        """Получить использование диска"""
        disk = psutil.disk_usage('/')
        return {
            'total': disk.total / (1024**3),  # GB
            'used': disk.used / (1024**3),
            'free': disk.free / (1024**3),
            'percent': disk.percent
        }
    
    @staticmethod
    def get_network_stats() -> Dict[str, float]:
        """Получить сетевую статистику"""
        net = psutil.net_io_counters()
        return {
            'sent': net.bytes_sent / (1024**2),  # MB
            'recv': net.bytes_recv / (1024**2)
        }
    
    @staticmethod
    def get_uptime() -> str:
        """Получить аптайм системы"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        return f"{days}д {hours}ч {minutes}м"
    
    @staticmethod
    def get_running_services() -> List[Dict[str, str]]:
        """Получить список работающих служб"""
        try:
            result = subprocess.run(
                ['systemctl', 'list-units', '--type=service', '--state=running', '--no-pager', '--plain'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            services = []
            for line in result.stdout.split('\n')[1:]:  # Пропускаем заголовок
                if line.strip() and '.service' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        service_name = parts[0].replace('.service', '')
                        services.append({
                            'name': service_name,
                            'status': parts[2],
                            'description': ' '.join(parts[4:]) if len(parts) > 4 else ''
                        })
            
            return services[:20]  # Ограничиваем 20 службами
        except Exception as e:
            return [{'name': 'Error', 'status': f'Ошибка: {str(e)}', 'description': ''}]
    
    @staticmethod
    def get_open_ports() -> List[Dict[str, any]]:
        """Получить список открытых портов"""
        try:
            connections = psutil.net_connections(kind='inet')
            ports = {}
            
            for conn in connections:
                if conn.status == 'LISTEN' and conn.laddr:
                    port = conn.laddr.port
                    if port not in ports:
                        try:
                            # Пытаемся получить имя процесса
                            process = psutil.Process(conn.pid) if conn.pid else None
                            process_name = process.name() if process else 'unknown'
                        except:
                            process_name = 'unknown'
                        
                        ports[port] = {
                            'port': port,
                            'address': conn.laddr.ip,
                            'process': process_name,
                            'pid': conn.pid
                        }
            
            # Сортируем по номеру порта
            return sorted(ports.values(), key=lambda x: x['port'])
        except Exception as e:
            return [{'port': 0, 'address': 'Error', 'process': str(e), 'pid': None}]
    
    @staticmethod
    def get_load_average() -> str:
        """Получить среднюю нагрузку"""
        try:
            load1, load5, load15 = psutil.getloadavg()
            cpu_count = psutil.cpu_count()
            return f"{load1:.2f} {load5:.2f} {load15:.2f} (cores: {cpu_count})"
        except:
            return "N/A"


class StatusMessageManager:
    """Менеджер для хранения ID сообщений со статусом"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.data = self._load()
    
    def _load(self) -> Dict:
        """Загрузить данные из файла"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save(self):
        """Сохранить данные в файл"""
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def add_channel(self, chat_id: int, message_id: int):
        """Добавить канал со статусным сообщением"""
        self.data[str(chat_id)] = message_id
        self._save()
    
    def get_channels(self) -> Dict[int, int]:
        """Получить все каналы с message_id"""
        return {int(k): v for k, v in self.data.items()}
    
    def remove_channel(self, chat_id: int):
        """Удалить канал"""
        if str(chat_id) in self.data:
            del self.data[str(chat_id)]
            self._save()


def format_status_message(monitor: ServerMonitor) -> str:
    """Форматировать статусное сообщение"""
    
    # Получаем все данные
    cpu = monitor.get_cpu_usage()
    memory = monitor.get_memory_usage()
    disk = monitor.get_disk_usage()
    network = monitor.get_network_stats()
    uptime = monitor.get_uptime()
    load = monitor.get_load_average()
    services = monitor.get_running_services()
    ports = monitor.get_open_ports()
    
    # Определяем статус (эмодзи)
    def get_status_emoji(percent):
        if percent < 60:
            return "🟢"
        elif percent < 80:
            return "🟡"
        else:
            return "🔴"
    
    cpu_status = get_status_emoji(cpu)
    mem_status = get_status_emoji(memory['percent'])
    disk_status = get_status_emoji(disk['percent'])
    
    # Формируем сообщение
    message = f"""
🖥 **СТАТУС СЕРВЕРА**
🕐 Обновлено: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
⏱ Аптайм: `{uptime}`

━━━━━━━━━━━━━━━━━━━━

📊 **РЕСУРСЫ**

{cpu_status} **CPU**: `{cpu:.1f}%`
📈 Load Average: `{load}`

{mem_status} **RAM**: `{memory['percent']:.1f}%` ({memory['used']:.1f}/{memory['total']:.1f} GB)

{disk_status} **Disk**: `{disk['percent']:.1f}%` ({disk['used']:.1f}/{disk['total']:.1f} GB)

🌐 **Network**: 
   ↓ `{network['recv']:.1f} MB` | ↑ `{network['sent']:.1f} MB`

━━━━━━━━━━━━━━━━━━━━

🔧 **СЛУЖБЫ** (работает {len(services)})
"""
    
    # Добавляем первые 10 служб
    for service in services[:10]:
        status_icon = "✅" if service['status'] == 'running' else "❌"
        message += f"{status_icon} `{service['name']}`\n"
    
    if len(services) > 10:
        message += f"... и еще {len(services) - 10} служб\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    message += f"🔌 **ОТКРЫТЫЕ ПОРТЫ** ({len(ports)})\n"
    
    # Добавляем первые 15 портов
    for port_info in ports[:15]:
        message += f"• Port `{port_info['port']}` - {port_info['process']}\n"
    
    if len(ports) > 15:
        message += f"... и еще {len(ports) - 15} портов\n"
    
    return message


async def update_status_messages(context: ContextTypes.DEFAULT_TYPE):
    """Обновить все статусные сообщения в каналах"""
    monitor = ServerMonitor()
    status_manager: StatusMessageManager = context.bot_data['status_manager']
    
    message_text = format_status_message(monitor)
    
    channels = status_manager.get_channels()
    for chat_id, message_id in channels.items():
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Ошибка обновления сообщения в {chat_id}: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🖥 **Бот мониторинга сервера**\n\n"
        "Добавь меня в канал и я создам пост со статусом сервера, "
        "который будет обновляться каждые 5 минут!\n\n"
        "**Команды:**\n"
        "/status - Текущий статус\n"
        "/services - Список служб\n"
        "/ports - Открытые порты\n"
        "/restart_service - Перезапустить службу\n"
        "/reboot - Перезагрузить сервер\n"
        "/logs - Просмотр логов\n"
        "/clear_logs - Очистка логов\n"
        "/close_port - Закрыть порт\n",
        parse_mode='Markdown'
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущий статус"""
    monitor = ServerMonitor()
    message_text = format_status_message(monitor)
    await update.message.reply_text(message_text, parse_mode='Markdown')


async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список служб"""
    monitor = ServerMonitor()
    services = monitor.get_running_services()
    
    message = "🔧 **РАБОТАЮЩИЕ СЛУЖБЫ**\n\n"
    for service in services:
        message += f"• `{service['name']}` - {service['status']}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def ports_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать открытые порты"""
    monitor = ServerMonitor()
    ports = monitor.get_open_ports()
    
    message = "🔌 **ОТКРЫТЫЕ ПОРТЫ**\n\n"
    for port_info in ports:
        message += f"• Port `{port_info['port']}` ({port_info['address']}) - {port_info['process']}"
        if port_info['pid']:
            message += f" [PID: {port_info['pid']}]"
        message += "\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def restart_service_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перезапустить службу"""
    user_id = update.effective_user.id
    
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /restart_service <имя_службы>\nПример: /restart_service nginx")
        return
    
    service_name = context.args[0]
    
    # Клавиатура подтверждения
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, перезапустить", callback_data=f"restart_service:{service_name}"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ Вы уверены что хотите перезапустить службу `{service_name}`?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def reboot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перезагрузить сервер"""
    user_id = update.effective_user.id
    
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, перезагрузить", callback_data="reboot_server"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ **ВНИМАНИЕ!** Вы уверены что хотите перезагрузить сервер?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр логов"""
    user_id = update.effective_user.id
    
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Использование: /logs <служба> [строк]\n"
            "Пример: /logs nginx 50\n"
            "Пример: /logs syslog"
        )
        return
    
    service = context.args[0]
    lines = int(context.args[1]) if len(context.args) > 1 else 50
    
    try:
        result = subprocess.run(
            ['journalctl', '-u', service, '-n', str(lines), '--no-pager'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        logs = result.stdout if result.stdout else result.stderr
        
        if len(logs) > 4000:
            logs = logs[-4000:]
        
        await update.message.reply_text(f"📋 **Логи {service}:**\n\n```\n{logs}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка получения логов: {str(e)}")


async def clear_logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистка логов"""
    user_id = update.effective_user.id
    
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("🗑 Очистить journalctl", callback_data="clear_journalctl"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ Выберите что очистить:",
        reply_markup=reply_markup
    )


async def close_port_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Закрыть порт (убить процесс)"""
    user_id = update.effective_user.id
    
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /close_port <номер_порта>\nПример: /close_port 8080")
        return
    
    try:
        port = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Неверный номер порта")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, закрыть порт", callback_data=f"close_port:{port}"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ Вы уверены что хотите закрыть порт `{port}`?\n"
        "Это завершит процесс использующий этот порт.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "cancel":
        await query.edit_message_text("❌ Операция отменена")
        return
    
    # Перезапуск службы
    if data.startswith("restart_service:"):
        service_name = data.split(":")[1]
        await query.edit_message_text(f"🔄 Перезапускаю службу `{service_name}`...", parse_mode='Markdown')
        
        try:
            result = subprocess.run(
                ['systemctl', 'restart', service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                await query.edit_message_text(f"✅ Служба `{service_name}` успешно перезапущена", parse_mode='Markdown')
            else:
                await query.edit_message_text(f"❌ Ошибка перезапуска:\n```\n{result.stderr}\n```", parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    
    # Перезагрузка сервера
    elif data == "reboot_server":
        await query.edit_message_text("🔄 Перезагружаю сервер через 10 секунд...")
        try:
            subprocess.Popen(['sleep', '10', '&&', 'reboot'], shell=False)
            await query.edit_message_text("✅ Команда перезагрузки отправлена. Сервер перезагрузится через 10 секунд.")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    
    # Очистка journalctl
    elif data == "clear_journalctl":
        await query.edit_message_text("🗑 Очищаю логи journalctl...")
        try:
            result = subprocess.run(
                ['journalctl', '--vacuum-time=1d'],
                capture_output=True,
                text=True,
                timeout=60
            )
            await query.edit_message_text(f"✅ Логи очищены:\n```\n{result.stdout}\n```", parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    
    # Закрытие порта
    elif data.startswith("close_port:"):
        port = int(data.split(":")[1])
        await query.edit_message_text(f"🔒 Закрываю порт {port}...")
        
        try:
            # Находим PID процесса на этом порту
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            pids = result.stdout.strip().split('\n')
            
            if pids and pids[0]:
                for pid in pids:
                    if pid:
                        subprocess.run(['kill', '-9', pid], timeout=5)
                
                await query.edit_message_text(f"✅ Порт {port} закрыт (завершено процессов: {len(pids)})")
            else:
                await query.edit_message_text(f"❌ Порт {port} не используется")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")


async def handle_new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик добавления бота в новый чат/канал"""
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            # Бот был добавлен в канал
            chat = update.effective_chat
            
            monitor = ServerMonitor()
            message_text = format_status_message(monitor)
            
            # Отправляем начальное сообщение
            sent_message = await context.bot.send_message(
                chat_id=chat.id,
                text=message_text,
                parse_mode='Markdown'
            )
            
            # Сохраняем ID сообщения
            status_manager: StatusMessageManager = context.bot_data['status_manager']
            status_manager.add_channel(chat.id, sent_message.message_id)
            
            print(f"Бот добавлен в канал {chat.id}, message_id: {sent_message.message_id}")


def main():
    """Основная функция"""
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ОШИБКА: Установите BOT_TOKEN в коде!")
        print("Получите токен у @BotFather в Telegram")
        return
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Инициализируем менеджер статусов
    status_manager = StatusMessageManager(STATUS_FILE)
    application.bot_data['status_manager'] = status_manager
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("services", services_command))
    application.add_handler(CommandHandler("ports", ports_command))
    application.add_handler(CommandHandler("restart_service", restart_service_command))
    application.add_handler(CommandHandler("reboot", reboot_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("clear_logs", clear_logs_command))
    application.add_handler(CommandHandler("close_port", close_port_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик добавления в канал
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat))
    
    # Запускаем периодическое обновление статусов
    job_queue = application.job_queue
    job_queue.run_repeating(update_status_messages, interval=UPDATE_INTERVAL, first=10)
    
    print("🤖 Бот запущен!")
    print(f"📊 Обновление статуса каждые {UPDATE_INTERVAL} секунд")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
