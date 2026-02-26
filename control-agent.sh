#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Telegram control helper

Usage:
  ./control-agent.sh escape "text"
  ./control-agent.sh logs [service]
  ./control-agent.sh diagnose [service]

Commands:
  escape     Escape text for Telegram MarkdownV2 parse mode.
  logs       Print the last 100 logs for a systemd service (default: server-monitor-bot).
  diagnose   Scan logs for Telegram parse errors and print a fix snippet.
USAGE
}

escape_markdown_v2() {
  local input=${1-}
  # Escape characters required by Telegram MarkdownV2.
  # See: https://core.telegram.org/bots/api#markdownv2-style
  python3 - "$input" <<'PY'
import re
import sys

text = sys.argv[1]
print(re.sub(r'([_\*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text), end='')
PY
}

show_logs() {
  local service=${1:-server-monitor-bot}
  journalctl -u "$service" -n 100 --no-pager
}

diagnose() {
  local service=${1:-server-monitor-bot}
  local logs
  logs=$(journalctl -u "$service" -n 250 --no-pager || true)

  if printf '%s' "$logs" | rg -q "BadRequest: Can't parse entities"; then
    cat <<'FIX'
Detected Telegram Markdown parsing failures.

Likely cause:
- Dynamic text is sent with parse_mode="MarkdownV2" (or "Markdown") without escaping.

Recommended Python fix:

from telegram.helpers import escape_markdown

safe_text = escape_markdown(dynamic_text, version=2)
await bot.send_message(chat_id=chat_id, text=safe_text, parse_mode="MarkdownV2")

If you do not need Markdown formatting, remove parse_mode entirely:
await bot.send_message(chat_id=chat_id, text=dynamic_text)
FIX
  else
    echo "No Telegram entity parse errors found in recent logs for $service."
  fi
}

main() {
  local cmd=${1:-}
  case "$cmd" in
    escape)
      shift
      escape_markdown_v2 "${1:-}"
      ;;
    logs)
      shift
      show_logs "${1:-server-monitor-bot}"
      ;;
    diagnose)
      shift
      diagnose "${1:-server-monitor-bot}"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
