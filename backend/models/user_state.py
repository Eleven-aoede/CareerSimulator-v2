from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class Phase(str, Enum):
    JOB_COLLECTION = "job_collection"
    PROFILE_COLLECTION = "profile_collection"
    STORY_SIMULATION = "story_simulation"
    COMPLETED = "completed"


@dataclass
class StoryState:
    meta: Optional[dict] = None
    current_node_id: Optional[str] = None
    generated_nodes: dict = field(default_factory=dict)
    choices: list = field(default_factory=list)
    scores: dict = field(default_factory=lambda: {"fit": 0, "stress": 0, "growth": 0})


@dataclass
class UserState:
    username: str
    phase: Phase = Phase.JOB_COLLECTION
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    job_input: Optional[dict] = None
    user_profile: Optional[dict] = None
    profile_skipped: bool = False
    conversation_history: list = field(default_factory=list)
    story_state: StoryState = field(default_factory=StoryState)
    session_id: Optional[str] = field(default=None, repr=False)

    def touch(self):
        self.last_active = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "phase": self.phase.value,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "job_input": self.job_input,
            "user_profile": self.user_profile,
            "profile_skipped": self.profile_skipped,
            "conversation_history": self.conversation_history,
            "story_state": {
                "meta": self.story_state.meta,
                "current_node_id": self.story_state.current_node_id,
                "generated_nodes": self.story_state.generated_nodes,
                "choices": self.story_state.choices,
                "scores": self.story_state.scores,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserState":
        story_data = data.get("story_state", {})
        story_state = StoryState(
            meta=story_data.get("meta"),
            current_node_id=story_data.get("current_node_id"),
            generated_nodes=story_data.get("generated_nodes", {}),
            choices=story_data.get("choices", []),
            scores=story_data.get("scores", {"fit": 0, "stress": 0, "growth": 0}),
        )
        return cls(
            username=data["username"],
            phase=Phase(data["phase"]),
            created_at=data.get("created_at", ""),
            last_active=data.get("last_active", ""),
            job_input=data.get("job_input"),
            user_profile=data.get("user_profile"),
            profile_skipped=data.get("profile_skipped", False),
            conversation_history=data.get("conversation_history", []),
            story_state=story_state,
        )
