import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from models.messages import ChatRequest
from models.session import Phase
from services.session_manager import session_manager
from services.conversation import process_message_stream
from services.story_generator import generate_story_stream

router = APIRouter(tags=["chat"])


@router.post("/sessions/{session_id}/chat/stream")
async def chat_stream(session_id: str, request: ChatRequest):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.phase not in (Phase.JOB_COLLECTION, Phase.PROFILE_COLLECTION):
        raise HTTPException(status_code=400, detail="当前阶段不支持聊天")

    async def event_generator():
        async for event in process_message_stream(session, request.message):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions/{session_id}/generate-story")
async def generate_story(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.phase != Phase.STORY_GENERATION:
        raise HTTPException(status_code=400, detail="尚未完成信息收集")

    async def event_generator():
        async for event in generate_story_stream(session):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
