#!/bin/bash
set -e

echo "Installing Telegram Control Agent..."
apt update
apt install -y python3 python3-venv python3-pip git

mkdir -p /opt/tg-control
cd /opt/tg-control

git clone https://github.com/tarpy-socdev/Telegram-control-agent.git .

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
echo "Installation done. Edit .env and run:"
echo "source venv/bin/activate && python bot/main.py"
