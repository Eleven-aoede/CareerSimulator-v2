import json
import asyncio
from typing import AsyncGenerator, Optional

from models.session import Session, Phase
from services.llm_client import llm_client
from services.prompt_engine import build_messages_for_story
from utils.json_extractor import extract_json_from_response
from config import settings


async def generate_story_stream(session: Session) -> AsyncGenerator[dict, None]:
    if session.phase != Phase.STORY_GENERATION:
        yield {"type": "error", "message": "当前阶段不支持生成故事"}
        return

    yield {"type": "progress", "message": "正在分析岗位信息..."}

    messages = build_messages_for_story(session)
    full_response = ""
    token_count = 0

    yield {"type": "progress", "message": "正在生成职业旅程..."}

    try:
        async for token in llm_client.chat_stream(
            messages, temperature=0.7, max_tokens=settings.max_tokens_story
        ):
            full_response += token
            token_count += 1
            if token_count % 200 == 0:
                yield {"type": "progress", "message": f"正在生成中（已生成 {token_count} 字）..."}
    except Exception as e:
        yield {"type": "error", "message": f"生成过程中出错：{str(e)[:50]}，请重试"}
        return

    if not full_response.strip():
        yield {"type": "error", "message": "AI 未返回内容，可能是网络超时，请重试"}
        return

    yield {"type": "progress", "message": "正在整理故事脚本..."}

    script = extract_json_from_response(full_response)

    if script and _validate_story_script(script):
        session.story_script = script
        session.phase = Phase.COMPLETE
        yield {"type": "complete", "script": script}
    else:
        yield {"type": "progress", "message": "首次生成未通过校验，正在重试..."}
        try:
            full_response = await llm_client.chat(
                messages, temperature=0.7, max_tokens=settings.max_tokens_story
            )
            script = extract_json_from_response(full_response)
            if script and _validate_story_script(script):
                session.story_script = script
                session.phase = Phase.COMPLETE
                yield {"type": "complete", "script": script}
            else:
                yield {"type": "error", "message": "故事生成失败，请刷新重试"}
        except Exception:
            yield {"type": "error", "message": "重试失败，请刷新重试"}


def _validate_story_script(script: dict) -> bool:
    if not isinstance(script, dict):
        return False

    for key in ("meta", "story", "endings"):
        if key not in script:
            return False

    story = script["story"]
    required_nodes = ["intro", "node1", "node2", "node3", "taskAction", "taskEmotion", "taskDifficulty"]
    for node in required_nodes:
        if node not in story:
            return False

    endings = script["endings"]
    for level in ("high", "mid", "low"):
        if level not in endings:
            return False

    return True
