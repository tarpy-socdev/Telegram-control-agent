#!/usr/bin/env bash
set -euo pipefail

SVC="tg-control-agent"
DIR="/opt/tg-control-agent"
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; N='\033[0m'

ok()   { echo -e "${G}[OK]${N} $1"; }
err()  { echo -e "${R}[ERR]${N} $1"; exit 1; }
info() { echo -e "${Y}[..]${N} $1"; }
need_root() { [ "$EUID" -eq 0 ] || err "Run as root: sudo $0 $*"; }

case "${1:-help}" in
  install)
    need_root
    info "Installing packages..."
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv lsof curl
    info "Creating virtualenv..."
    python3 -m venv "$DIR/venv"
    "$DIR/venv/bin/pip" install -q \
      "python-telegram-bot[job-queue]==20.7" \
      psutil==5.9.6 \
      python-dotenv==1.0.0
    info "Creating systemd service..."
    cat > "/etc/systemd/system/${SVC}.service" << 'SVC_EOF'
[Unit]
Description=Telegram Control Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tg-control-agent
ExecStart=/opt/tg-control-agent/venv/bin/python -m bot.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC_EOF
    systemctl daemon-reload
    systemctl enable "$SVC"
    ok "Install complete!"
    echo ""
    echo "  Next steps:"
    echo "  1. Edit .env — set BOT_TOKEN and ADMIN_IDS"
    echo "  2. sudo ./install.sh start"
    ;;

  start)
    need_root
    systemctl start "$SVC"; sleep 2
    systemctl is-active --quiet "$SVC" \
      && ok "Bot started!" \
      || err "Failed to start. Check: ./install.sh logs"
    ;;

  stop)
    need_root
    systemctl stop "$SVC" && ok "Bot stopped"
    ;;

  restart)
    need_root
    systemctl restart "$SVC"; sleep 2
    systemctl is-active --quiet "$SVC" \
      && ok "Bot restarted!" \
      || err "Failed. Check: ./install.sh logs"
    ;;

  status)
    systemctl status "$SVC" --no-pager -l
    ;;

  logs)
    journalctl -u "$SVC" -n "${2:-50}" --no-pager
    ;;

  logs-live)
    journalctl -u "$SVC" -f
    ;;

  help|*)
    echo "Usage: sudo ./install.sh {install|start|stop|restart|status|logs [N]|logs-live}"
    ;;
esac
