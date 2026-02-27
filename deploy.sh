#!/bin/bash
# deploy.sh — автоматический деплой бота на сервер

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Конфиг
SERVER="${SERVER:-tarpy@82.202.158.235}"
REMOTE_PATH="/opt/tg-control-agent"
LOCAL_PATH="${LOCAL_PATH:-.}"

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_ok() { echo -e "${GREEN}✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Проверка аргументов
if [ $# -lt 1 ]; then
    echo -e "${BLUE}Telegram Control Agent — Deploy Script${NC}"
    echo ""
    echo "Использование:"
    echo "  ./deploy.sh push       — загрузить изменения на GitHub"
    echo "  ./deploy.sh pull       — обновить бот на сервере"
    echo "  ./deploy.sh restart    — перезапустить бот"
    echo "  ./deploy.sh logs       — показать логи"
    echo "  ./deploy.sh full       — push + pull + restart"
    echo ""
    exit 1
fi

case "$1" in
    push)
        print_info "Загрузка на GitHub..."
        git add -A
        git commit -m "update: bot improvements $(date '+%Y-%m-%d %H:%M')" || print_warn "Нет изменений"
        git push origin main
        print_ok "Загружено на GitHub"
        ;;
    
    pull)
        print_info "Загрузка update_bot_final.py на сервер..."
        scp ./update_bot_final.py "$SERVER:$REMOTE_PATH/"
        
        print_info "Обновление бота..."
        ssh "$SERVER" "cd $REMOTE_PATH && python3 update_bot_final.py"
        
        print_ok "Бот обновлён"
        ;;
    
    restart)
        print_info "Перезапуск бота..."
        ssh "$SERVER" "cd $REMOTE_PATH && ./install.sh restart"
        print_ok "Бот перезапущен"
        ;;
    
    logs)
        print_info "Логи бота (последние 20):"
        ssh "$SERVER" "cd $REMOTE_PATH && ./install.sh logs 20"
        ;;
    
    full)
        print_info "Полный цикл: push → pull → restart"
        $0 push && sleep 2 && $0 pull && sleep 2 && $0 restart
        print_ok "Деплой завершён!"
        ;;
    
    *)
        print_error "Неизвестная команда: $1"
        exit 1
        ;;
esac
