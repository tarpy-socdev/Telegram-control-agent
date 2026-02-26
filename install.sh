#!/bin/bash

set -e

echo "Installing Telegram Control Agent..."

apt update
apt install -y python3 python3-venv python3-pip git

# папка
mkdir -p /opt/tg-control
cd /opt/tg-control

echo "Cloning repo..."
git clone https://github.com/tarpy-socdev/Telegram-control-agent.git .

echo "Creating venv..."
python3 -m venv venv
source venv/bin/activate

echo "Installing deps..."
pip install -r requirements.txt

echo "Creating env..."
cp .env.example .env

echo "Done."
echo "Edit .env and run:"
echo "source venv/bin/activate && python bot/main.py"
