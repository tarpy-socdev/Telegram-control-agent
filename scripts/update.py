#!/usr/bin/env python3
"""
update.py — Обновление Telegram Control Agent до финальной версии
Запускай на сервере: python3 update.py

Скачивает свежий код с GitHub и перезапускает бота.
"""
import os
import sys
import subprocess
import urllib.request
import shutil
from datetime import datetime

BOT_DIR  = "/opt/tg-control-agent"
REPO_RAW = "https://raw.githubusercontent.com/tarpy-socdev/Telegram-control-agent/refs/heads/wwwwwww"
SVC_NAME = "tg-control-agent"

# Files to update from GitHub
FILES = [
    "bot/config.py",
    "bot/main.py",
    "bot/core/controller.py",
    "bot/monitor/server.py",
    "bot/storage/status_store.py",
    "bot/telegram/formatter.py",
    "bot/telegram/handlers.py",
    "bot/telegram/keyboards.py",
    "install.sh",
    "requirements.txt",
]

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[94m"; N = "\033[0m"
def ok(m):   print(f"{G}[OK]{N} {m}")
def err(m):  print(f"{R}[ERR]{N} {m}")
def info(m): print(f"{B}[..]{N} {m}")
def warn(m): print(f"{Y}[!!]{N} {m}")

def run(cmd, check=False):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        err(f"Command failed: {cmd}\n{r.stderr}")
        sys.exit(1)
    return r


def backup():
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_dir = f"{BOT_DIR}/backups/{ts}"
    os.makedirs(bak_dir, exist_ok=True)
    for f in FILES:
        src = os.path.join(BOT_DIR, f)
        if os.path.exists(src):
            dst = os.path.join(bak_dir, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    ok(f"Backup: {bak_dir}")
    return bak_dir


def download_file(rel_path):
    url  = f"{REPO_RAW}/{rel_path}"
    dest = os.path.join(BOT_DIR, rel_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        err(f"Failed {rel_path}: {e}")
        return False


def main():
    print("=" * 50)
    print("  Telegram Control Agent — Update")
    print("=" * 50)
    print()

    if not os.path.exists(BOT_DIR):
        err(f"Bot not installed at {BOT_DIR}")
        print("Run setup_final.py first.")
        sys.exit(1)

    info("Creating backup...")
    bak = backup()

    info(f"Downloading {len(FILES)} files from GitHub...")
    failed = []
    for f in FILES:
        if download_file(f):
            ok(f)
        else:
            failed.append(f)

    if failed:
        warn(f"{len(failed)} files failed to download:")
        for f in failed: print(f"  - {f}")
        warn("Update may be incomplete. Check your connection.")

    # Make install.sh executable
    sh = os.path.join(BOT_DIR, "install.sh")
    if os.path.exists(sh):
        os.chmod(sh, 0o755)

    # touch __init__ files just in case
    for pkg in ["bot", "bot/core", "bot/monitor", "bot/storage", "bot/telegram"]:
        init = os.path.join(BOT_DIR, pkg, "__init__.py")
        if not os.path.exists(init):
            open(init, "w").close()
            ok(f"{pkg}/__init__.py created")

    print()
    info("Restarting bot...")
    r = run(f"systemctl restart {SVC_NAME}")
    if r.returncode == 0:
        import time; time.sleep(2)
        r2 = run(f"systemctl is-active {SVC_NAME}")
        if r2.stdout.strip() == "active":
            ok("Bot restarted successfully!")
        else:
            warn("Bot may not be running. Check logs:")
            print(f"  journalctl -u {SVC_NAME} -n 20 --no-pager")
    else:
        warn(f"Restart failed: {r.stderr}")

    print()
    print("=" * 50)
    print(f"  Done! Backup at: {bak}")
    print()
    print("  Check status:")
    print(f"  sudo ./install.sh logs 20")
    print("=" * 50)


if __name__ == "__main__":
    main()
