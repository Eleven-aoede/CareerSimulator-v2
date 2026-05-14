from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time
import uuid


class Phase(str, Enum):
    JOB_COLLECTION = "job_collection"
    PROFILE_COLLECTION = "profile_collection"
    STORY_GENERATION = "story_generation"
    COMPLETE = "complete"


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phase: Phase = Phase.JOB_COLLECTION
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    conversation_history: list[dict] = field(default_factory=list)
    job_input: Optional[dict] = None
    user_profile: Optional[dict] = None
    story_script: Optional[dict] = None
    profile_skipped: bool = False

    def touch(self):
        self.last_active = time.time()

    def is_expired(self, ttl: int) -> bool:
        return time.time() - self.last_active > ttl
