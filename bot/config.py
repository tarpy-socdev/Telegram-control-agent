# bot/config.py
# Конфигурация — читается из .env файла, токен НИКОГДА не в коде

import os
from dotenv import load_dotenv

# Загружаем .env из корня проекта
load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val or val.startswith("PUT_"):
        raise RuntimeError(
            f"\n\n❌ Переменная {key} не настроена!\n"
            f"   Скопируй .env.example → .env и заполни значения.\n"
        )
    return val


def _parse_ids(raw: str) -> list[int]:
    result = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return result


BOT_TOKEN: str = _require("BOT_TOKEN")
ADMIN_IDS: list[int] = _parse_ids(os.getenv("ADMIN_IDS", ""))
UPDATE_INTERVAL: int = int(os.getenv("UPDATE_INTERVAL", "300"))
