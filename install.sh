#!/usr/bin/env bash
# install.sh — универсальный менеджер Telegram Control Agent
set -euo pipefail

# ─── Конфиг ───────────────────────────────────────────────────────────────────
SERVICE_NAME="tg-control-agent"
BOT_DIR="/opt/tg-control-agent"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
REPO_URL="https://github.com/tarpy-socdev/Telegram-control-agent.git"
BRANCH="main"

# ─── Цвета ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $*${NC}"; }
err()  { echo -e "${RED}❌ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
info() { echo -e "${BLUE}ℹ️  $*${NC}"; }
hdr()  { echo -e "\n${CYAN}══════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}══════════════════════════════════════${NC}"; }

# ─── Root check ───────────────────────────────────────────────────────────────
need_root() {
  [[ "$EUID" -eq 0 ]] || { err "Нужен root: sudo $0 $*"; exit 1; }
}

# ─────────────────────────────────────────────────────────────────────────────
# INSTALL
# ─────────────────────────────────────────────────────────────────────────────
cmd_install() {
  need_root
  hdr "Установка Telegram Control Agent"

  # Зависимости
  info "Устанавливаю системные зависимости..."
  apt-get update -qq
  apt-get install -y python3 python3-pip python3-venv git lsof curl wget >/dev/null 2>&1
  ok "Системные зависимости установлены"

  # Директория
  mkdir -p "$BOT_DIR/backups"

  # Клонирование / обновление
  if [[ -d "$BOT_DIR/.git" ]]; then
    info "Репозиторий уже существует — обновляю..."
    git -C "$BOT_DIR" pull --ff-only
  else
    info "Клонирую репозиторий..."
    git clone -b "$BRANCH" "$REPO_URL" "$BOT_DIR"
  fi
  ok "Код загружен в $BOT_DIR"

  # Venv + pip
  info "Создаю виртуальное окружение..."
  python3 -m venv "$BOT_DIR/venv"
  info "Устанавливаю Python зависимости..."
  "$BOT_DIR/venv/bin/pip" install -q --upgrade pip
  "$BOT_DIR/venv/bin/pip" install -q -r "$BOT_DIR/requirements.txt"
  ok "Python зависимости установлены"

  # .env
  if [[ ! -f "$BOT_DIR/.env" ]]; then
    cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
    warn "Создан .env — нужно заполнить токен и ID!"
    warn "Запусти: sudo $0 configure"
  fi

  # systemd
  info "Создаю systemd сервис..."
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Telegram Control Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${BOT_DIR}
EnvironmentFile=${BOT_DIR}/.env
ExecStart=${BOT_DIR}/venv/bin/python -m bot.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME" >/dev/null 2>&1
  ok "Systemd сервис создан и включён"

  echo ""
  ok "Установка завершена!"
  echo ""
  echo "  📝 Следующие шаги:"
  echo "  1. sudo $0 configure    — ввести токен и ID"
  echo "  2. sudo $0 start        — запустить бота"
  echo "  3. Добавь бота в канал как администратора"
  echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURE
# ─────────────────────────────────────────────────────────────────────────────
cmd_configure() {
  need_root
  [[ -f "$BOT_DIR/.env" ]] || { err ".env не найден. Сначала: sudo $0 install"; exit 1; }

  hdr "Настройка бота"

  echo "Получи токен у @BotFather в Telegram"
  read -rp "BOT_TOKEN: " bot_token
  [[ -z "$bot_token" ]] && { err "Токен не может быть пустым"; exit 1; }

  echo ""
  echo "Узнай свой ID у @userinfobot"
  read -rp "ADMIN_IDS (через запятую): " admin_ids
  [[ -z "$admin_ids" ]] && warn "ADMIN_IDS не указаны — команды управления доступны всем!"

  echo ""
  read -rp "UPDATE_INTERVAL в секундах [300]: " interval
  interval="${interval:-300}"

  # Пишем .env
  cat > "$BOT_DIR/.env" <<EOF
BOT_TOKEN=${bot_token}
ADMIN_IDS=${admin_ids}
UPDATE_INTERVAL=${interval}
EOF

  ok "Конфигурация сохранена в $BOT_DIR/.env"
  info "Перезапусти бота: sudo $0 restart"
}

cmd_show_config() {
  [[ -f "$BOT_DIR/.env" ]] || { err ".env не найден"; exit 1; }

  hdr "Текущая конфигурация"
  local token admin interval
  token=$(grep "^BOT_TOKEN=" "$BOT_DIR/.env" | cut -d= -f2-)
  admin=$(grep "^ADMIN_IDS=" "$BOT_DIR/.env" | cut -d= -f2-)
  interval=$(grep "^UPDATE_INTERVAL=" "$BOT_DIR/.env" | cut -d= -f2-)

  if [[ "$token" == "PUT_YOUR_TOKEN_HERE" || -z "$token" ]]; then
    warn "BOT_TOKEN: не настроен"
  else
    local masked="${token:0:10}...${token: -10}"
    ok "BOT_TOKEN: $masked"
  fi

  [[ -z "$admin" ]] && warn "ADMIN_IDS: не настроены" || ok "ADMIN_IDS: [$admin]"
  info "UPDATE_INTERVAL: ${interval}с ($(( ${interval:-300} / 60 )) мин)"
}

# ─────────────────────────────────────────────────────────────────────────────
# SERVICE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
cmd_start() {
  need_root
  systemctl start "$SERVICE_NAME"
  sleep 2
  if systemctl is-active --quiet "$SERVICE_NAME"; then
    ok "Бот запущен!"
    systemctl status "$SERVICE_NAME" --no-pager -l | head -15
  else
    err "Не удалось запустить. Логи: sudo $0 logs 50"
  fi
}

cmd_stop() {
  need_root
  systemctl stop "$SERVICE_NAME"
  ok "Бот остановлен"
}

cmd_restart() {
  need_root
  systemctl restart "$SERVICE_NAME"
  sleep 2
  systemctl is-active --quiet "$SERVICE_NAME" && ok "Бот перезапущен!" || err "Ошибка запуска. Логи: sudo $0 logs 50"
}

cmd_status() {
  systemctl status "$SERVICE_NAME" --no-pager -l
}

# ─────────────────────────────────────────────────────────────────────────────
# LOGS
# ─────────────────────────────────────────────────────────────────────────────
cmd_logs() {
  local n="${1:-100}"
  journalctl -u "$SERVICE_NAME" -n "$n" --no-pager
}

cmd_logs_live() {
  info "Логи в реальном времени (Ctrl+C для выхода):"
  journalctl -u "$SERVICE_NAME" -f
}

# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSE
# ─────────────────────────────────────────────────────────────────────────────
cmd_diagnose() {
  hdr "Диагностика"
  local errors=0

  systemctl is-active --quiet "$SERVICE_NAME" \
    && ok "Сервис запущен" \
    || { err "Сервис не запущен! Запусти: sudo $0 start"; errors=$((errors+1)); }

  [[ -f "$BOT_DIR/.env" ]] || { err ".env не найден"; errors=$((errors+1)); }

  if [[ -f "$BOT_DIR/.env" ]]; then
    local tok
    tok=$(grep "^BOT_TOKEN=" "$BOT_DIR/.env" | cut -d= -f2-)
    [[ "$tok" == "PUT_YOUR_TOKEN_HERE" || -z "$tok" ]] \
      && { err "BOT_TOKEN не настроен!"; errors=$((errors+1)); } \
      || ok "BOT_TOKEN настроен"
  fi

  command -v python3 &>/dev/null && ok "Python3 установлен" || { err "Python3 не найден"; errors=$((errors+1)); }

  if [[ -x "$BOT_DIR/venv/bin/python" ]]; then
    ok "Venv создан"
    "$BOT_DIR/venv/bin/python" -c "import telegram" 2>/dev/null \
      && ok "python-telegram-bot установлен" \
      || { err "python-telegram-bot не найден"; errors=$((errors+1)); }
    "$BOT_DIR/venv/bin/python" -c "import psutil" 2>/dev/null \
      && ok "psutil установлен" \
      || { err "psutil не найден"; errors=$((errors+1)); }
  else
    err "Venv не найден! Запусти: sudo $0 install"
    errors=$((errors+1))
  fi

  # Ошибки в логах
  local logs
  logs=$(journalctl -u "$SERVICE_NAME" -n 100 --no-pager 2>/dev/null || true)
  echo "$logs" | grep -q "Can't parse entities" \
    && { err "Ошибка парсинга Markdown в логах!"; errors=$((errors+1)); }
  echo "$logs" | grep -q "Unauthorized" \
    && { err "Неверный BOT_TOKEN в логах!"; errors=$((errors+1)); }

  echo ""
  [[ $errors -eq 0 ]] && ok "Все проверки пройдены!" || warn "Найдено ошибок: $errors"
}

# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────
cmd_update() {
  need_root
  hdr "Обновление бота"

  [[ -d "$BOT_DIR/.git" ]] || { err "Репозиторий не найден. Запусти: sudo $0 install"; exit 1; }

  # Бэкап конфига
  local bak="$BOT_DIR/backups/.env.$(date +%Y%m%d_%H%M%S)"
  [[ -f "$BOT_DIR/.env" ]] && { cp "$BOT_DIR/.env" "$bak"; ok "Бэкап .env: $bak"; }

  info "Получаю обновления с GitHub..."
  git -C "$BOT_DIR" pull --ff-only

  info "Обновляю Python зависимости..."
  "$BOT_DIR/venv/bin/pip" install -q --upgrade -r "$BOT_DIR/requirements.txt"

  # Восстанавливаем .env если он был
  [[ -f "$bak" && ! -f "$BOT_DIR/.env" ]] && cp "$bak" "$BOT_DIR/.env"

  ok "Обновление завершено"
  info "Перезапусти бота: sudo $0 restart"
}

# ─────────────────────────────────────────────────────────────────────────────
# BACKUP / RESTORE
# ─────────────────────────────────────────────────────────────────────────────
cmd_backup() {
  need_root
  local file="$BOT_DIR/backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz"
  tar -czf "$file" -C "$BOT_DIR" .env status_messages.json 2>/dev/null || true
  ok "Бэкап: $file"
  # Хранить только последние 10
  ls -t "$BOT_DIR/backups/backup_"*.tar.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
}

cmd_restore() {
  need_root
  local file="${1:-}"
  if [[ -z "$file" ]]; then
    err "Укажи файл: sudo $0 restore <файл>"
    echo "Доступные бэкапы:"
    ls -lh "$BOT_DIR/backups/"backup_*.tar.gz 2>/dev/null || echo "  нет бэкапов"
    exit 1
  fi
  [[ -f "$file" ]] || { err "Файл не найден: $file"; exit 1; }
  tar -xzf "$file" -C "$BOT_DIR"
  ok "Восстановлено из $file"
  info "Перезапусти: sudo $0 restart"
}

# ─────────────────────────────────────────────────────────────────────────────
# UNINSTALL
# ─────────────────────────────────────────────────────────────────────────────
cmd_uninstall() {
  need_root
  warn "Это удалит бота и все данные!"
  read -rp "Продолжить? (y/N): " c
  [[ "$c" =~ ^[yY]$ ]] || { info "Отменено"; exit 0; }

  systemctl stop "$SERVICE_NAME" 2>/dev/null || true
  systemctl disable "$SERVICE_NAME" 2>/dev/null || true
  rm -f "$SERVICE_FILE"
  systemctl daemon-reload
  rm -rf "$BOT_DIR"
  ok "Бот удалён"
}

# ─────────────────────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────────────────────
cmd_escape() {
  python3 -c "
import re, sys
text = sys.argv[1]
print(re.sub(r'([_\*\[\]()~\`>#+\-=|{}.!\\\\])', r'\\\\\\\1', text), end='')
" "${1:-}"
}

cmd_test_status() {
  python3 - <<'PY'
import psutil
from datetime import datetime

cpu = psutil.cpu_percent(interval=1)
mem = psutil.virtual_memory()
disk = psutil.disk_usage('/')

def emo(p):
    return "🟢" if p < 60 else ("🟡" if p < 80 else "🔴")

print(f"""
🖥 СТАТУС СЕРВЕРА (ТЕСТ)
🕐 {datetime.now():%Y-%m-%d %H:%M:%S}

{emo(cpu)} CPU:  {cpu:.1f}%
{emo(mem.percent)} RAM:  {mem.percent:.1f}% ({mem.used/1024**3:.1f}/{mem.total/1024**3:.1f} GB)
{emo(disk.percent)} Disk: {disk.percent:.1f}% ({disk.used/1024**3:.1f}/{disk.total/1024**3:.1f} GB)

✅ Генерация статуса работает!
""")
PY
}

# ─────────────────────────────────────────────────────────────────────────────
# HELP
# ─────────────────────────────────────────────────────────────────────────────
cmd_help() {
  cat <<'HELP'
🤖 Telegram Control Agent — менеджер

УСТАНОВКА:
  sudo ./install.sh install          Установить бота
  sudo ./install.sh uninstall        Удалить бота

УПРАВЛЕНИЕ:
  sudo ./install.sh start            Запустить
  sudo ./install.sh stop             Остановить
  sudo ./install.sh restart          Перезапустить
  sudo ./install.sh status           Статус сервиса

НАСТРОЙКА:
  sudo ./install.sh configure        Настроить токен и ID
  sudo ./install.sh show-config      Показать конфигурацию

ЛОГИ:
  sudo ./install.sh logs [N]         Последние N строк (по умолчанию 100)
  sudo ./install.sh logs-live        Логи в реальном времени
  sudo ./install.sh diagnose         Диагностика проблем

ОБСЛУЖИВАНИЕ:
  sudo ./install.sh update           Обновить с GitHub
  sudo ./install.sh backup           Создать бэкап
  sudo ./install.sh restore <file>   Восстановить из бэкапа

УТИЛИТЫ:
  ./install.sh escape "text"         Экранировать текст для Telegram
  ./install.sh test-status           Тест генерации статуса
HELP
}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
main() {
  local cmd="${1:-help}"
  shift || true

  case "$cmd" in
    install)      cmd_install ;;
    uninstall)    cmd_uninstall ;;
    start)        cmd_start ;;
    stop)         cmd_stop ;;
    restart)      cmd_restart ;;
    status)       cmd_status ;;
    configure)    cmd_configure ;;
    show-config)  cmd_show_config ;;
    logs)         cmd_logs "${1:-100}" ;;
    logs-live)    cmd_logs_live ;;
    diagnose)     cmd_diagnose ;;
    update)       cmd_update ;;
    backup)       cmd_backup ;;
    restore)      cmd_restore "${1:-}" ;;
    escape)       cmd_escape "${1:-}" ;;
    test-status)  cmd_test_status ;;
    help|-h|--help) cmd_help ;;
    *)
      err "Неизвестная команда: $cmd"
      cmd_help
      exit 1 ;;
  esac
}

main "$@"
