import json as json_mod
import re
from typing import Generator

from models.user_state import UserState, Phase
from services.llm_client import llm_client
from services.prompt_engine import build_messages_for_chat
from utils.json_extractor import extract_tagged_json, strip_extraction_tag

_MARKDOWN_RE = re.compile(r'[*_~`#]')
_OPTIONS_RE = re.compile(r'<options>\s*(\[.*?\])\s*</options>', re.DOTALL)


def _sanitize_token(token: str) -> str:
    return _MARKDOWN_RE.sub('', token)


def _extract_options(text: str) -> tuple[str, list[str]]:
    match = _OPTIONS_RE.search(text)
    if match:
        try:
            options = json_mod.loads(match.group(1))
            cleaned = text[:match.start()].rstrip()
            return cleaned, options
        except (json_mod.JSONDecodeError, ValueError):
            pass
    return text, []

GREETING = (
    "嗨，我是小可，是这次职业旅程的带领者。\n"
    "在我们正式出发之前，你可以先告诉我，你想去看看哪个职业吗？（可以选择也可以输入～）\n"
    "如果你知道一些相关信息可以现在或者之后告诉我，如果实在不清楚的也可以直接说不知道。\n"
    "提示：岗位相关信息可以来自某个你感兴趣的公司岗位的JD、招聘要求噢"
    '<options>["产品经理", "程序员"]</options>'
)

TRANSITION_TEXT = (
    "每一份工作都有特别的任务和氛围，即便看起来像是在做差不多的事，"
    "真正走进去以后，节奏、压力落点，还有让人觉得有成就感的地方，往往都不太一样呢。\n"
    "所以在出发之前，我想多认识你一点点呀。"
    "这样等我们真的走进这份职业的时候，你看到的那些细节、卡住的时刻，"
    "还有会让你眼睛亮一下的瞬间，也许会让你更有共鸣，也能帮你更好理解这个岗位。"
)


def initialize_session(user_state: UserState) -> str:
    user_state.conversation_history.append(
        {"role": "assistant", "content": GREETING}
    )
    return GREETING


def process_message_stream(
    user_state: UserState, user_message: str
) -> Generator[dict, None, None]:
    user_state.touch()
    user_state.conversation_history.append({"role": "user", "content": user_message})

    messages = build_messages_for_chat(user_state)
    full_response = ""
    pending_buffer = ""
    in_extraction = False
    in_options = False
    done_sent = False

    for token in llm_client.chat_stream(messages, username=user_state.username):
        full_response += token

        if in_extraction or in_options:
            continue

        pending_buffer += token

        if "<" in pending_buffer:
            if "<extraction>" in pending_buffer:
                before_tag = pending_buffer.split("<extraction>")[0]
                if before_tag:
                    yield {"type": "token", "content": _sanitize_token(before_tag)}
                in_extraction = True
                pending_buffer = ""

                if user_state.phase == Phase.JOB_COLLECTION:
                    user_state.phase = Phase.PROFILE_COLLECTION
                elif user_state.phase == Phase.PROFILE_COLLECTION:
                    user_state.phase = Phase.STORY_SIMULATION

                yield {
                    "type": "done",
                    "phase": user_state.phase.value,
                    "phase_complete": True,
                    "transition_text": TRANSITION_TEXT if user_state.phase == Phase.PROFILE_COLLECTION else None,
                }
                done_sent = True

            elif "<options>" in pending_buffer:
                before_tag = pending_buffer.split("<options>")[0]
                if before_tag:
                    yield {"type": "token", "content": _sanitize_token(before_tag)}
                in_options = True
                pending_buffer = ""

            elif not _tag_prefix_match(pending_buffer):
                yield {"type": "token", "content": _sanitize_token(pending_buffer)}
                pending_buffer = ""
        else:
            yield {"type": "token", "content": _sanitize_token(pending_buffer)}
            pending_buffer = ""

    if pending_buffer and not in_extraction and not in_options:
        clean = pending_buffer.split("<extraction>")[0] if "<extraction>" in pending_buffer else pending_buffer
        clean = clean.split("<options>")[0] if "<options>" in clean else clean
        if clean:
            yield {"type": "token", "content": _sanitize_token(clean)}

    extraction = extract_tagged_json(full_response)
    raw_visible = strip_extraction_tag(full_response)
    _, options = _extract_options(raw_visible)

    # 保留 <options> 标签在历史中，LLM 需要上下文
    history_content = _sanitize_token(raw_visible)
    user_state.conversation_history.append(
        {"role": "assistant", "content": history_content}
    )

    if extraction and not done_sent:
        if user_state.phase == Phase.JOB_COLLECTION:
            user_state.phase = Phase.PROFILE_COLLECTION
        elif user_state.phase == Phase.PROFILE_COLLECTION:
            user_state.phase = Phase.STORY_SIMULATION

    if extraction:
        if user_state.phase == Phase.PROFILE_COLLECTION:
            user_state.job_input = extraction
        elif user_state.phase == Phase.STORY_SIMULATION:
            user_state.user_profile = extraction.get("user_profile", extraction)

    if options:
        yield {"type": "options", "items": options}

    if not done_sent:
        yield {
            "type": "done",
            "phase": user_state.phase.value,
            "phase_complete": bool(extraction),
            "transition_text": TRANSITION_TEXT if extraction and user_state.phase == Phase.PROFILE_COLLECTION else None,
        }


def _tag_prefix_match(buffer: str) -> bool:
    tail = buffer[buffer.rindex("<"):]
    return "<extraction>".startswith(tail) or "<options>".startswith(tail)


def skip_profile(user_state: UserState) -> str:
    user_state.touch()

    profile_user_msgs = [
        msg["content"] for msg in user_state.conversation_history
        if msg["role"] == "user"
    ]

    if len(profile_user_msgs) >= 2 and user_state.phase == Phase.PROFILE_COLLECTION:
        user_state.user_profile = {"raw_answers": profile_user_msgs[1:], "partial": True}
        user_state.profile_skipped = False
        user_state.phase = Phase.STORY_SIMULATION
        return "好的，我已经记住了刚才聊到的部分～接下来我会根据已有的了解为你生成职业旅程。"

    user_state.profile_skipped = True
    user_state.phase = Phase.STORY_SIMULATION
    return "好的，那我们直接出发吧～我会用一个比较通用的视角来为你生成这段职业旅程。"
