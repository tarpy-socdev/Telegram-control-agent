# Telegram Control Agent

Small helper script for diagnosing Telegram bot failures from `systemd` logs, focused on the common error:

`telegram.error.BadRequest: Can't parse entities: can't find end of the entity ...`

## Why this happens

When a bot sends dynamic text with `parse_mode="Markdown"` or `parse_mode="MarkdownV2"`, characters like `_`, `*`, `(`, `)`, `[` and others can break Telegram entity parsing unless escaped.

## Script usage

```bash
./control-agent.sh diagnose server-monitor-bot
./control-agent.sh logs server-monitor-bot
./control-agent.sh escape "Disk /dev/sda1 is 92% (critical)!"
```

## Recommended code fix in Python bot

```python
from telegram.helpers import escape_markdown

safe = escape_markdown(dynamic_text, version=2)
await bot.send_message(chat_id=chat_id, text=safe, parse_mode="MarkdownV2")
```

If markdown formatting is not required, remove `parse_mode` to send raw text safely.
