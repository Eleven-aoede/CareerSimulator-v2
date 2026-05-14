import asyncio
from typing import Optional

from config import settings
from models.session import Session, Phase


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> Session:
        session = Session()
        async with self._lock:
            self._sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session and session.is_expired(settings.session_ttl_seconds):
                del self._sessions[session_id]
                return None
            return session

    async def delete_session(self, session_id: str) -> bool:
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    async def cleanup_expired(self):
        async with self._lock:
            expired = [
                sid
                for sid, s in self._sessions.items()
                if s.is_expired(settings.session_ttl_seconds)
            ]
            for sid in expired:
                del self._sessions[sid]


session_manager = SessionManager()
