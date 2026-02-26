# status_store.py
# Хранилище ID сообщений

import json
import os

class StatusStore:
    def __init__(self, filename="status_messages.json"):
        self.filename = filename
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=2)

    def add_channel(self, chat_id, message_id):
        self.data[str(chat_id)] = message_id
        self._save()

    def get_channels(self):
        return {int(k): v for k, v in self.data.items()}

    def remove_channel(self, chat_id):
        if str(chat_id) in self.data:
            del self.data[str(chat_id)]
            self._save()
