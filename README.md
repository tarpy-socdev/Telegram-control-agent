# Telegram Control Agent

Server monitoring bot for Telegram. Monitors CPU, RAM, disk, services and ports. Sends status updates to linked channels/groups.

## Quick Install (new server)

```bash
# 1. Download setup script
python3 -c "
import urllib.request
urllib.request.urlretrieve(
    'https://raw.githubusercontent.com/tarpy-socdev/Telegram-control-agent/refs/heads/wwwwwww/setup_final.py',
    '/tmp/setup_final.py'
)
print('Downloaded')
"

# 2. Set your token and admin ID
nano /tmp/setup_final.py
# Change: BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
# Change: ADMIN_IDS = "YOUR_ADMIN_ID"

# 3. Run
python3 /tmp/setup_final.py
```

## Update existing installation

```bash
cd /opt/tg-control-agent
python3 scripts/update.py
```

## Project structure

```
/opt/tg-control-agent/
├── .env                    # config (BOT_TOKEN, ADMIN_IDS, UPDATE_INTERVAL)
├── .env.example
├── install.sh              # service management
├── requirements.txt
├── status_messages.json    # auto-created, stores channel bindings + stats
├── bot/
│   ├── config.py           # loads .env
│   ├── main.py             # entry point, job scheduler
│   ├── core/
│   │   └── controller.py   # systemctl, SSH, ports
│   ├── monitor/
│   │   └── server.py       # CPU, RAM, disk, network, services
│   ├── storage/
│   │   └── status_store.py # JSON storage for channels + settings
│   └── telegram/
│       ├── formatter.py    # message formatting
│       ├── handlers.py     # commands + callbacks + jobs
│       └── keyboards.py    # inline keyboards
└── scripts/
    └── update.py           # pull updates from GitHub
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show status + main menu |
| `/ping <host>` | Ping a host |
| `/services` | List running services |
| `/ports` | List open ports |
| `/logs <service> [N]` | Show last N log lines |
| `/restart_service <n>` | Restart a service |
| `/stop_service <n>` | Stop a service |
| `/reboot` | Reboot server |
| `/close_port <port>` | Kill process on port |
| `/link_channel <id>` | Link channel by ID |
| `/broadcast <text>` | Send to all linked chats |
| `/report` | Daily stats report |
| `/set_alerts <cpu> <ram> <disk>` | Set alert thresholds |
| `/set_report_time 09:00` | Set daily report time |
| `/set_reboot_time 04:00` | Set auto-reboot time |
| `/add_ssh_key <pubkey>` | Add SSH public key |
| `/upload` | Upload file to server |

## Manage service

```bash
sudo ./install.sh start
sudo ./install.sh stop
sudo ./install.sh restart
sudo ./install.sh logs 50
sudo ./install.sh logs-live
sudo ./install.sh status
```

## Notes

- Bot token: get from [@BotFather](https://t.me/BotFather)
- Admin ID: get from [@userinfobot](https://t.me/userinfobot)
- Channel ID: forward any channel post to @userinfobot, then use `/link_channel -100XXXXXXXXX`
- SSH disable uses `systemctl stop ssh.socket` to prevent socket-activation restart
