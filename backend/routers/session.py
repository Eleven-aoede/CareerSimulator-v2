from fastapi import APIRouter, HTTPException

from models.messages import SessionResponse, SessionStateResponse, SkipProfileResponse
from models.session import Phase
from services.session_manager import session_manager
from services.conversation import initialize_session, skip_profile

router = APIRouter(tags=["session"])


@router.post("/sessions", response_model=SessionResponse)
async def create_session():
    session = await session_manager.create_session()
    greeting = initialize_session(session)
    return SessionResponse(
        session_id=session.session_id,
        phase=session.phase.value,
        greeting=greeting,
    )


@router.get("/sessions/{session_id}", response_model=SessionStateResponse)
async def get_session(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionStateResponse(
        session_id=session.session_id,
        phase=session.phase.value,
        job_input=session.job_input,
        user_profile=session.user_profile,
        profile_skipped=session.profile_skipped,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = await session_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}


@router.post("/sessions/{session_id}/skip-profile", response_model=SkipProfileResponse)
async def skip_profile_endpoint(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.phase != Phase.PROFILE_COLLECTION:
        raise HTTPException(status_code=400, detail="只能在画像采集阶段跳过")
    message = await skip_profile(session)
    return SkipProfileResponse(phase=session.phase.value, message=message)
