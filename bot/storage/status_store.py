# bot/storage/status_store.py
# Хранилище ID сообщений со статусом в каналах

import json
import os


class StatusStore:
    def __init__(self, filename: str = "status_messages.json"):
        self.filename = filename
        self.data: dict = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=2)

    def add_channel(self, chat_id: int, message_id: int) -> None:
        self.data[str(chat_id)] = message_id
        self._save()

    def get_channels(self) -> dict[int, int]:
        return {int(k): v for k, v in self.data.items()}

    def remove_channel(self, chat_id: int) -> None:
        if str(chat_id) in self.data:
            del self.data[str(chat_id)]
            self._save()
