import os
import json
import re
import shutil
from datetime import datetime
from uuid import uuid4
from filelock import FileLock

from config import settings
from models.user_state import UserState


def _extract_preview(conversation_history: list) -> str:
    for msg in conversation_history:
        if msg.get("role") == "user":
            return msg.get("content", "")[:20]
    return ""


class PersistenceService:
    def __init__(self):
        self.base_dir = os.path.abspath(settings.data_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _sanitize_username(self, username: str) -> str:
        sanitized = re.sub(r'[/\\.\x00]', '_', username.strip())
        return sanitized[:64] if sanitized else "_unnamed"

    def _user_dir(self, username: str) -> str:
        return os.path.join(self.base_dir, self._sanitize_username(username))

    def _session_dir(self, username: str, session_id: str) -> str:
        return os.path.join(self._user_dir(username), session_id)

    def _lock_path(self, username: str) -> str:
        return self._user_dir(username) + ".lock"

    def _sessions_index_path(self, username: str) -> str:
        return os.path.join(self._user_dir(username), "sessions.json")

    def _generate_session_id(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:4]

    # --- Migration ---

    def _needs_migration(self, username: str) -> bool:
        user_dir = self._user_dir(username)
        old_state = os.path.join(user_dir, "state.json")
        sessions_index = self._sessions_index_path(username)
        return os.path.exists(old_state) and not os.path.exists(sessions_index)

    def _migrate_old_format(self, username: str) -> None:
        user_dir = self._user_dir(username)
        old_state_path = os.path.join(user_dir, "state.json")

        with open(old_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        created_at = data.get("created_at", datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(created_at)
            session_id = dt.strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:4]
        except (ValueError, TypeError):
            session_id = self._generate_session_id()

        preview = _extract_preview(data.get("conversation_history", []))

        session_dir = os.path.join(user_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)

        files_to_move = ["state.json", "history.json", "llm_log.json", "system_log.json"]
        for fname in files_to_move:
            src = os.path.join(user_dir, fname)
            if os.path.exists(src):
                shutil.move(src, os.path.join(session_dir, fname))

        sessions = [{
            "session_id": session_id,
            "created_at": created_at,
            "last_active": data.get("last_active", created_at),
            "phase": data.get("phase", "job_collection"),
            "preview": preview,
        }]
        with open(self._sessions_index_path(username), "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)

    # --- Sessions index ---

    def _load_sessions_index(self, username: str) -> list:
        path = self._sessions_index_path(username)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_sessions_index(self, username: str, sessions: list) -> None:
        path = self._sessions_index_path(username)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)

    def _update_session_entry(self, username: str, session_id: str, **kwargs) -> None:
        sessions = self._load_sessions_index(username)
        for entry in sessions:
            if entry["session_id"] == session_id:
                entry.update(kwargs)
                break
        self._save_sessions_index(username, sessions)

    # --- Public API ---

    def user_exists(self, username: str) -> bool:
        user_dir = self._user_dir(username)
        if not os.path.isdir(user_dir):
            return False
        if os.path.exists(self._sessions_index_path(username)):
            return True
        if os.path.exists(os.path.join(user_dir, "state.json")):
            return True
        return False

    def list_sessions(self, username: str) -> list:
        with FileLock(self._lock_path(username)):
            if self._needs_migration(username):
                self._migrate_old_format(username)
            return self._load_sessions_index(username)

    def create_session(self, username: str) -> str:
        user_dir = self._user_dir(username)
        os.makedirs(user_dir, exist_ok=True)
        session_id = self._generate_session_id()
        session_dir = os.path.join(user_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)

        now = datetime.now().isoformat()
        with FileLock(self._lock_path(username)):
            if self._needs_migration(username):
                self._migrate_old_format(username)
            sessions = self._load_sessions_index(username)
            sessions.append({
                "session_id": session_id,
                "created_at": now,
                "last_active": now,
                "phase": "job_collection",
                "preview": "",
            })
            self._save_sessions_index(username, sessions)
        return session_id

    def delete_session(self, username: str, session_id: str) -> None:
        session_dir = self._session_dir(username, session_id)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
        with FileLock(self._lock_path(username)):
            sessions = self._load_sessions_index(username)
            sessions = [s for s in sessions if s["session_id"] != session_id]
            self._save_sessions_index(username, sessions)

    def session_exists(self, username: str, session_id: str) -> bool:
        session_dir = self._session_dir(username, session_id)
        return os.path.exists(os.path.join(session_dir, "state.json"))

    def load_state(self, username: str, session_id: str) -> UserState:
        state_file = os.path.join(self._session_dir(username, session_id), "state.json")
        with FileLock(self._lock_path(username)):
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        user_state = UserState.from_dict(data)
        user_state.session_id = session_id
        return user_state

    def save_state(self, user_state: UserState, session_id: str) -> None:
        session_dir = self._session_dir(user_state.username, session_id)
        os.makedirs(session_dir, exist_ok=True)
        state_file = os.path.join(session_dir, "state.json")
        with FileLock(self._lock_path(user_state.username)):
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(user_state.to_dict(), f, ensure_ascii=False, indent=2)

            sessions = self._load_sessions_index(user_state.username)
            for entry in sessions:
                if entry["session_id"] == session_id:
                    entry["last_active"] = user_state.last_active
                    entry["phase"] = user_state.phase.value
                    if not entry.get("preview"):
                        entry["preview"] = _extract_preview(user_state.conversation_history)
                    break
            self._save_sessions_index(user_state.username, sessions)

    def clear_session(self, username: str, session_id: str) -> None:
        self.delete_session(username, session_id)

    def append_history(self, username: str, session_id: str, entry: dict) -> None:
        session_dir = self._session_dir(username, session_id)
        os.makedirs(session_dir, exist_ok=True)
        history_file = os.path.join(session_dir, "history.json")
        entry["timestamp"] = datetime.now().isoformat()
        with FileLock(self._lock_path(username)):
            history = []
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            history.append(entry)
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

    def append_llm_log(self, username: str, session_id: str, entry: dict) -> None:
        session_dir = self._session_dir(username, session_id)
        os.makedirs(session_dir, exist_ok=True)
        log_file = os.path.join(session_dir, "llm_log.json")
        entry["timestamp"] = datetime.now().isoformat()
        with FileLock(self._lock_path(username)):
            logs = []
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            logs.append(entry)
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

    def append_system_log(self, username: str, session_id: str, entry: dict) -> None:
        session_dir = self._session_dir(username, session_id)
        os.makedirs(session_dir, exist_ok=True)
        log_file = os.path.join(session_dir, "system_log.json")
        entry["timestamp"] = datetime.now().isoformat()
        with FileLock(self._lock_path(username)):
            logs = []
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            logs.append(entry)
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

    def list_users(self) -> list[dict]:
        users = []
        if not os.path.isdir(self.base_dir):
            return users
        for name in sorted(os.listdir(self.base_dir)):
            user_dir = os.path.join(self.base_dir, name)
            if not os.path.isdir(user_dir):
                continue
            sessions_file = os.path.join(user_dir, "sessions.json")
            old_state = os.path.join(user_dir, "state.json")
            if os.path.exists(sessions_file):
                try:
                    with open(sessions_file, "r", encoding="utf-8") as f:
                        sessions = json.load(f)
                    if sessions:
                        latest = max(sessions, key=lambda s: s.get("last_active", ""))
                        users.append({
                            "username": name,
                            "session_count": len(sessions),
                            "last_active": latest.get("last_active", ""),
                        })
                except (json.JSONDecodeError, OSError):
                    continue
            elif os.path.exists(old_state):
                try:
                    with open(old_state, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    users.append({
                        "username": data.get("username", name),
                        "session_count": 1,
                        "last_active": data.get("last_active", ""),
                    })
                except (json.JSONDecodeError, OSError):
                    continue
        return users

    def load_llm_log(self, username: str, session_id: str) -> list:
        log_file = os.path.join(self._session_dir(username, session_id), "llm_log.json")
        if not os.path.exists(log_file):
            return []
        with FileLock(self._lock_path(username)):
            with open(log_file, "r", encoding="utf-8") as f:
                return json.load(f)

    def load_system_log(self, username: str, session_id: str) -> list:
        log_file = os.path.join(self._session_dir(username, session_id), "system_log.json")
        if not os.path.exists(log_file):
            return []
        with FileLock(self._lock_path(username)):
            with open(log_file, "r", encoding="utf-8") as f:
                return json.load(f)


persistence = PersistenceService()
