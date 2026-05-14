from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str


class SessionResponse(BaseModel):
    session_id: str
    phase: str
    greeting: Optional[str] = None


class SessionStateResponse(BaseModel):
    session_id: str
    phase: str
    job_input: Optional[dict] = None
    user_profile: Optional[dict] = None
    profile_skipped: bool = False


class SkipProfileResponse(BaseModel):
    phase: str
    message: str
