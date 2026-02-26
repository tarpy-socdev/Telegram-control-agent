#!/usr/bin/env bash
set -euo pipefail

# ====================================
# Telegram Server Monitor Bot
# Универсальный установщик и менеджер
# ====================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="server-monitor-bot"
BOT_DIR="/opt/server-monitor-bot"
BOT_FILE="$BOT_DIR/server_monitor_bot.py"
SERVICE_FILE="/etc/systemd/system/server-monitor-bot.service"

# Utility functions
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

check_root() {
  if [ "$EUID" -ne 0 ]; then 
    print_error "Требуются права root. Используй: sudo $0 $*"
    exit 1
  fi
}

usage() {
  cat <<'USAGE'
🤖 Telegram Server Monitor Bot - Универсальный менеджер

УСТАНОВКА:
  sudo ./install.sh install          Установить бота
  sudo ./install.sh uninstall        Удалить бота

УПРАВЛЕНИЕ:
  sudo ./install.sh start            Запустить
  sudo ./install.sh stop             Остановить
  sudo ./install.sh restart          Перезапустить
  sudo ./install.sh status           Статус сервиса
  
НАСТРОЙКА:
  sudo ./install.sh configure        Настроить токен и админов
  sudo ./install.sh show-config      Показать конфигурацию
  
ЛОГИ И ДИАГНОСТИКА:
  sudo ./install.sh logs [N]         Последние N строк логов (по умолчанию 100)
  sudo ./install.sh logs-live        Логи в реальном времени
  sudo ./install.sh diagnose         Диагностика проблем
  
ОБСЛУЖИВАНИЕ:
  sudo ./install.sh update           Обновить с GitHub
  sudo ./install.sh backup           Создать бэкап
  sudo ./install.sh restore <file>   Восстановить из бэкапа

УТИЛИТЫ:
  ./install.sh escape "text"         Экранировать для Telegram MarkdownV2
  ./install.sh test-ping <host>      Тест ping функции
  ./install.sh test-status           Тест генерации статуса

HELP:
  ./install.sh help                  Показать эту справку

ПРИМЕРЫ:
  sudo ./install.sh install
  sudo ./install.sh configure
  sudo ./install.sh start
  sudo ./install.sh logs-live
  sudo ./install.sh update

USAGE
}

# ============= INSTALLATION =============

install_bot() {
  check_root
  
  echo "======================================"
  echo "Установка Telegram Server Monitor Bot"
  echo "======================================"
  echo ""
  
  # Check if already installed
  if [ -f "$BOT_FILE" ]; then
    print_warning "Бот уже установлен в $BOT_DIR"
    echo -n "Переустановить? (y/N): "
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
      print_info "Отменено"
      exit 0
    fi
  fi
  
  # Install dependencies
  print_info "Устанавливаю зависимости..."
  apt update -qq
  apt install -y python3 python3-pip lsof wget curl >/dev/null 2>&1
  
  print_info "Устанавливаю Python библиотеки..."
  pip3 install 'python-telegram-bot[job-queue]==20.7' psutil==5.9.6 --break-system-packages -q
  
  # Create directory
  print_info "Создаю директорию..."
  mkdir -p "$BOT_DIR"
  mkdir -p "$BOT_DIR/backups"
  
  # Download bot file
  print_info "Скачиваю бота..."
  local bot_url="https://raw.githubusercontent.com/tarpy-socdev/Telegram-control-agent/dev/server_monitor_bot.py"
  
  if wget -q "$bot_url" -O "$BOT_FILE"; then
    chmod +x "$BOT_FILE"
    print_success "Бот скачан"
  else
    # If download fails, check if file exists locally
    if [ -f "./server_monitor_bot.py" ]; then
      print_warning "Не удалось скачать с GitHub, использую локальный файл"
      cp ./server_monitor_bot.py "$BOT_FILE"
      chmod +x "$BOT_FILE"
    else
      print_error "Не удалось получить файл бота"
      exit 1
    fi
  fi
  
  # Create systemd service
  print_info "Создаю systemd сервис..."
  cat > "$SERVICE_FILE" <<'SERVICE'
[Unit]
Description=Telegram Server Monitor Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/server-monitor-bot
ExecStart=/usr/bin/python3 /opt/server-monitor-bot/server_monitor_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE
  
  systemctl daemon-reload
  print_success "Сервис создан"
  
  echo ""
  print_success "Установка завершена!"
  echo ""
  echo "======================================"
  echo "📝 СЛЕДУЮЩИЕ ШАГИ:"
  echo "======================================"
  echo ""
  echo "1. Создай бота в @BotFather и получи токен"
  echo ""
  echo "2. Узнай свой ID у @userinfobot"
  echo ""
  echo "3. Настрой бота:"
  echo "   sudo ./install.sh configure"
  echo ""
  echo "4. Запусти бота:"
  echo "   sudo ./install.sh start"
  echo ""
  echo "5. Добавь бота в канал как администратора"
  echo ""
  echo "======================================"
  echo ""
}

uninstall_bot() {
  check_root
  
  print_warning "Это удалит бота и все его данные!"
  echo -n "Продолжить? (y/N): "
  read -r confirm
  
  if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    print_info "Отменено"
    exit 0
  fi
  
  print_info "Останавливаю бота..."
  systemctl stop "$SERVICE_NAME" 2>/dev/null || true
  systemctl disable "$SERVICE_NAME" 2>/dev/null || true
  
  print_info "Удаляю сервис..."
  rm -f "$SERVICE_FILE"
  systemctl daemon-reload
  
  print_info "Удаляю файлы..."
  rm -rf "$BOT_DIR"
  
  print_success "Бот удален"
}

# ============= SERVICE MANAGEMENT =============

start_service() {
  check_root
  print_info "Запускаю бота..."
  systemctl start "$SERVICE_NAME"
  sleep 2
  if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_success "Бот успешно запущен!"
    systemctl status "$SERVICE_NAME" --no-pager -l | head -15
  else
    print_error "Не удалось запустить бота. Проверь логи:"
    echo "  sudo ./install.sh logs 50"
  fi
}

stop_service() {
  check_root
  print_info "Останавливаю бота..."
  systemctl stop "$SERVICE_NAME"
  print_success "Бот остановлен"
}

restart_service() {
  check_root
  print_info "Перезапускаю бота..."
  systemctl restart "$SERVICE_NAME"
  sleep 2
  if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_success "Бот успешно перезапущен!"
    systemctl status "$SERVICE_NAME" --no-pager -l | head -15
  else
    print_error "Не удалось перезапустить бота. Проверь логи"
  fi
}

show_status() {
  systemctl status "$SERVICE_NAME" --no-pager -l
}

# ============= CONFIGURATION =============

configure_bot() {
  check_root
  
  if [ ! -f "$BOT_FILE" ]; then
    print_error "Бот не установлен. Сначала запусти: sudo ./install.sh install"
    exit 1
  fi
  
  print_info "Интерактивная настройка бота"
  echo ""
  
  # Get bot token
  echo "Получи токен у @BotFather в Telegram"
  echo -n "Введи BOT_TOKEN: "
  read -r bot_token
  
  if [ -z "$bot_token" ]; then
    print_error "Токен не может быть пустым"
    exit 1
  fi
  
  # Get admin IDs
  echo ""
  echo "Узнай свой ID у @userinfobot"
  echo -n "Введи ADMIN_IDS через запятую: "
  read -r admin_ids
  
  if [ -z "$admin_ids" ]; then
    print_warning "ADMIN_IDS не указаны - команды управления будут недоступны"
    admin_ids=""
  fi
  
  # Get update interval
  echo ""
  echo -n "Интервал обновления в секундах [300]: "
  read -r update_interval
  update_interval=${update_interval:-300}
  
  # Backup current config
  local backup_file="$BOT_FILE.backup.$(date +%Y%m%d_%H%M%S)"
  cp "$BOT_FILE" "$backup_file"
  print_success "Создан бэкап: $backup_file"
  
  # Update config
  sed -i "s|BOT_TOKEN = \".*\"|BOT_TOKEN = \"$bot_token\"|" "$BOT_FILE"
  
  if [ -n "$admin_ids" ]; then
    formatted_ids=$(echo "$admin_ids" | sed 's/,/, /g')
    sed -i "s|ADMIN_IDS = \[.*\]|ADMIN_IDS = [$formatted_ids]|" "$BOT_FILE"
  fi
  
  sed -i "s|UPDATE_INTERVAL = .*|UPDATE_INTERVAL = $update_interval|" "$BOT_FILE"
  
  print_success "Конфигурация обновлена!"
  echo ""
  print_info "Перезапусти бота: sudo ./install.sh restart"
}

show_config() {
  if [ ! -f "$BOT_FILE" ]; then
    print_error "Бот не установлен"
    exit 1
  fi
  
  print_info "Текущая конфигурация:"
  echo ""
  
  local bot_token=$(grep "^BOT_TOKEN = " "$BOT_FILE" | cut -d'"' -f2)
  local admin_ids=$(grep "^ADMIN_IDS = " "$BOT_FILE" | cut -d'[' -f2 | cut -d']' -f1)
  local update_interval=$(grep "^UPDATE_INTERVAL = " "$BOT_FILE" | awk '{print $3}')
  
  if [ "$bot_token" = "YOUR_BOT_TOKEN_HERE" ]; then
    print_warning "BOT_TOKEN: Не настроен"
  else
    local masked_token="${bot_token:0:10}...${bot_token: -10}"
    echo "BOT_TOKEN: $masked_token"
  fi
  
  if [ -z "$admin_ids" ]; then
    print_warning "ADMIN_IDS: Не настроены"
  else
    echo "ADMIN_IDS: [$admin_ids]"
  fi
  
  echo "UPDATE_INTERVAL: $update_interval секунд ($(($update_interval / 60)) минут)"
}

# ============= LOGS & DIAGNOSTICS =============

show_logs() {
  local lines=${1:-100}
  print_info "Последние $lines строк логов:"
  journalctl -u "$SERVICE_NAME" -n "$lines" --no-pager
}

show_logs_live() {
  print_info "Логи в реальном времени (Ctrl+C для выхода):"
  journalctl -u "$SERVICE_NAME" -f
}

diagnose() {
  print_info "Диагностика бота..."
  echo ""
  
  local has_errors=0
  
  # Check if bot is running
  if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_success "Бот запущен"
  else
    print_error "Бот не запущен!"
    print_info "Запусти: sudo ./install.sh start"
    has_errors=1
  fi
  
  # Check config
  if [ -f "$BOT_FILE" ]; then
    if grep -q "YOUR_BOT_TOKEN_HERE" "$BOT_FILE"; then
      print_error "BOT_TOKEN не настроен!"
      print_info "Настрой: sudo ./install.sh configure"
      has_errors=1
    else
      print_success "BOT_TOKEN настроен"
    fi
    
    if grep -q "ADMIN_IDS = \[\]" "$BOT_FILE"; then
      print_warning "ADMIN_IDS пуст - команды управления недоступны"
      print_info "Настрой: sudo ./install.sh configure"
    else
      print_success "ADMIN_IDS настроены"
    fi
  fi
  
  # Check dependencies
  if command -v python3 &> /dev/null; then
    print_success "Python3 установлен"
  else
    print_error "Python3 не установлен!"
    has_errors=1
  fi
  
  if python3 -c "import telegram" 2>/dev/null; then
    print_success "python-telegram-bot установлен"
  else
    print_error "python-telegram-bot не установлен!"
    print_info "Установи: pip3 install 'python-telegram-bot[job-queue]' --break-system-packages"
    has_errors=1
  fi
  
  if python3 -c "import psutil" 2>/dev/null; then
    print_success "psutil установлен"
  else
    print_error "psutil не установлен!"
    has_errors=1
  fi
  
  # Check logs for errors
  echo ""
  print_info "Проверка логов на ошибки..."
  local logs=$(journalctl -u "$SERVICE_NAME" -n 250 --no-pager 2>/dev/null || echo "")
  
  if echo "$logs" | grep -q "BadRequest: Can't parse entities"; then
    print_error "Ошибка парсинга Markdown!"
    echo ""
    echo "Решение:"
    echo "  1. Обнови бота: sudo ./install.sh update"
    echo "  2. Перезапусти: sudo ./install.sh restart"
    has_errors=1
  fi
  
  if echo "$logs" | grep -q "Unauthorized"; then
    print_error "Неверный BOT_TOKEN!"
    print_info "Проверь токен: sudo ./install.sh show-config"
    has_errors=1
  fi
  
  echo ""
  if [ $has_errors -eq 0 ]; then
    print_success "Все проверки пройдены! Бот работает корректно."
  else
    print_warning "Обнаружены проблемы. Исправь их и запусти диагностику снова."
  fi
}

# ============= MAINTENANCE =============

update_bot() {
  check_root
  
  print_info "Обновление бота с GitHub..."
  
  local repo_url="https://raw.githubusercontent.com/tarpy-socdev/Telegram-control-agent/dev/server_monitor_bot.py"
  local temp_file="/tmp/server_monitor_bot_new.py"
  
  # Download new version
  if ! wget -q "$repo_url" -O "$temp_file"; then
    print_error "Не удалось скачать обновление с GitHub"
    exit 1
  fi
  
  # Backup current version
  local backup_file="$BOT_DIR/backups/bot_update_$(date +%Y%m%d_%H%M%S).py"
  cp "$BOT_FILE" "$backup_file"
  print_success "Создан бэкап: $backup_file"
  
  # Get current config
  local bot_token=$(grep "^BOT_TOKEN = " "$BOT_FILE" | cut -d'"' -f2)
  local admin_ids=$(grep "^ADMIN_IDS = " "$BOT_FILE" | cut -d'[' -f2 | cut -d']' -f1)
  local update_interval=$(grep "^UPDATE_INTERVAL = " "$BOT_FILE" | awk '{print $3}')
  
  # Update file
  cp "$temp_file" "$BOT_FILE"
  
  # Restore config
  sed -i "s|BOT_TOKEN = \".*\"|BOT_TOKEN = \"$bot_token\"|" "$BOT_FILE"
  if [ -n "$admin_ids" ]; then
    sed -i "s|ADMIN_IDS = \[.*\]|ADMIN_IDS = [$admin_ids]|" "$BOT_FILE"
  fi
  sed -i "s|UPDATE_INTERVAL = .*|UPDATE_INTERVAL = $update_interval|" "$BOT_FILE"
  
  print_success "Бот обновлен! Конфигурация сохранена."
  print_info "Перезапусти бота: sudo ./install.sh restart"
}

backup_bot() {
  check_root
  
  local backup_dir="$BOT_DIR/backups"
  mkdir -p "$backup_dir"
  
  local backup_file="$backup_dir/bot_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
  
  tar -czf "$backup_file" -C "$BOT_DIR" server_monitor_bot.py status_messages.json 2>/dev/null || true
  
  print_success "Бэкап создан: $backup_file"
  
  # Keep only last 10 backups
  ls -t "$backup_dir"/bot_backup_*.tar.gz | tail -n +11 | xargs rm -f 2>/dev/null || true
}

restore_bot() {
  check_root
  
  local backup_file=$1
  
  if [ -z "$backup_file" ]; then
    print_error "Укажи файл бэкапа"
    echo ""
    echo "Доступные бэкапы:"
    ls -lh "$BOT_DIR/backups/"*.tar.gz 2>/dev/null || echo "Нет бэкапов"
    exit 1
  fi
  
  if [ ! -f "$backup_file" ]; then
    print_error "Файл не найден: $backup_file"
    exit 1
  fi
  
  print_warning "Это перезапишет текущую конфигурацию!"
  echo -n "Продолжить? (y/N): "
  read -r confirm
  
  if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    print_info "Отменено"
    exit 0
  fi
  
  tar -xzf "$backup_file" -C "$BOT_DIR"
  print_success "Бэкап восстановлен"
  print_info "Перезапусти: sudo ./install.sh restart"
}

# ============= UTILITIES =============

escape_markdown_v2() {
  local input=${1-}
  python3 - "$input" <<'PY'
import re, sys
text = sys.argv[1]
print(re.sub(r'([_\*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text), end='')
PY
}

test_ping() {
  local host=${1:-google.com}
  print_info "Тестирую ping $host..."
  
  python3 <<PYCODE
import subprocess
host = "$host"
try:
    result = subprocess.run(['ping', '-c', '4', host], 
                          capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print(f"✅ Ping {host} успешен!")
        output = result.stdout
        if 'rtt min/avg/max/mdev' in output or 'round-trip' in output:
            stats_line = [line for line in output.split('\n') 
                         if 'min/avg/max' in line or 'round-trip' in line]
            if stats_line:
                print(stats_line[0])
    else:
        print(f"❌ Ping {host} не удался")
except Exception as e:
    print(f"❌ Ошибка: {e}")
PYCODE
}

test_status() {
  print_info "Генерирую тестовое статусное сообщение..."
  
  python3 <<'PYCODE'
import psutil
from datetime import datetime

cpu = psutil.cpu_percent(interval=1)
mem = psutil.virtual_memory()
disk = psutil.disk_usage('/')

def get_emoji(percent):
    if percent < 60: return "🟢"
    elif percent < 80: return "🟡"
    else: return "🔴"

print(f"""
🖥 СТАТУС СЕРВЕРА (ТЕСТ)
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{get_emoji(cpu)} CPU: {cpu:.1f}%
{get_emoji(mem.percent)} RAM: {mem.percent:.1f}% ({mem.used/1024**3:.1f}/{mem.total/1024**3:.1f} GB)
{get_emoji(disk.percent)} Disk: {disk.percent:.1f}% ({disk.used/1024**3:.1f}/{disk.total/1024**3:.1f} GB)

✅ Генерация статуса работает!
""")
PYCODE
}

# ============= MAIN =============

main() {
  local cmd=${1:-help}
  
  case "$cmd" in
    # Installation
    install)
      install_bot
      ;;
    uninstall)
      uninstall_bot
      ;;
    
    # Service management
    start)
      start_service
      ;;
    stop)
      stop_service
      ;;
    restart)
      restart_service
      ;;
    status)
      show_status
      ;;
    
    # Configuration
    configure)
      configure_bot
      ;;
    show-config)
      show_config
      ;;
    
    # Logs & diagnostics
    logs)
      shift
      show_logs "${1:-100}"
      ;;
    logs-live)
      show_logs_live
      ;;
    diagnose)
      diagnose
      ;;
    
    # Maintenance
    update)
      update_bot
      ;;
    backup)
      backup_bot
      ;;
    restore)
      shift
      restore_bot "${1:-}"
      ;;
    
    # Utilities (no root needed)
    escape)
      shift
      escape_markdown_v2 "${1:-}"
      ;;
    test-ping)
      shift
      test_ping "${1:-google.com}"
      ;;
    test-status)
      test_status
      ;;
    
    # Help
    help|-h|--help)
      usage
      ;;
    
    *)
      print_error "Неизвестная команда: $cmd"
      echo ""
      usage
      exit 1
      ;;
  esac
}

main "$@"
