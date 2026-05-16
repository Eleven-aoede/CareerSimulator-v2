import os
import json
import re
from datetime import datetime
from filelock import FileLock

from config import settings
from models.user_state import UserState


class PersistenceService:
    def __init__(self):
        self.base_dir = os.path.abspath(settings.data_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _sanitize_username(self, username: str) -> str:
        sanitized = re.sub(r'[/\\.\x00]', '_', username.strip())
        return sanitized[:64] if sanitized else "_unnamed"

    def _user_dir(self, username: str) -> str:
        return os.path.join(self.base_dir, self._sanitize_username(username))

    def _lock_path(self, username: str) -> str:
        return self._user_dir(username) + ".lock"

    def user_exists(self, username: str) -> bool:
        state_file = os.path.join(self._user_dir(username), "state.json")
        return os.path.exists(state_file)

    def load_state(self, username: str) -> UserState:
        state_file = os.path.join(self._user_dir(username), "state.json")
        with FileLock(self._lock_path(username)):
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        return UserState.from_dict(data)

    def save_state(self, user_state: UserState) -> None:
        user_dir = self._user_dir(user_state.username)
        os.makedirs(user_dir, exist_ok=True)
        state_file = os.path.join(user_dir, "state.json")
        with FileLock(self._lock_path(user_state.username)):
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(user_state.to_dict(), f, ensure_ascii=False, indent=2)

    def clear_user(self, username: str) -> None:
        user_dir = self._user_dir(username)
        if os.path.exists(user_dir):
            import shutil
            shutil.rmtree(user_dir)

    def append_history(self, username: str, entry: dict) -> None:
        user_dir = self._user_dir(username)
        os.makedirs(user_dir, exist_ok=True)
        history_file = os.path.join(user_dir, "history.json")
        entry["timestamp"] = datetime.now().isoformat()
        with FileLock(self._lock_path(username)):
            history = []
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            history.append(entry)
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

    def append_llm_log(self, username: str, entry: dict) -> None:
        user_dir = self._user_dir(username)
        os.makedirs(user_dir, exist_ok=True)
        log_file = os.path.join(user_dir, "llm_log.json")
        entry["timestamp"] = datetime.now().isoformat()
        with FileLock(self._lock_path(username)):
            logs = []
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            logs.append(entry)
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

    def append_system_log(self, username: str, entry: dict) -> None:
        user_dir = self._user_dir(username)
        os.makedirs(user_dir, exist_ok=True)
        log_file = os.path.join(user_dir, "system_log.json")
        entry["timestamp"] = datetime.now().isoformat()
        with FileLock(self._lock_path(username)):
            logs = []
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            logs.append(entry)
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)


persistence = PersistenceService()
