from typing import AsyncGenerator

from models.session import Session, Phase
from services.llm_client import llm_client
from services.prompt_engine import build_messages_for_chat
from utils.json_extractor import extract_tagged_json, strip_extraction_tag

GREETING = (
    "嗨，我是小可，是这次职业旅程的带领者～"
    "在我们正式出发之前，你可以先告诉我，你想去看看哪个职业吗？"
    "如果能再告诉我一些相关信息就更好啦，比如岗位名称、平时主要在做什么、"
    "公司所在行业，还有公司规模这些，我就能为你定制这段旅程了噢！"
)

TRANSITION_TEXT = (
    "每一份工作都有特别的任务和氛围，即便看起来像是在做差不多的事，"
    "真正走进去以后，节奏、压力落点，还有让人觉得有成就感的地方，往往都不太一样呢。\n"
    "所以在出发之前，我想多认识你一点点呀。"
    "这样等我们真的走进这份职业的时候，你看到的那些细节、卡住的时刻，"
    "还有会让你眼睛亮一下的瞬间，也许会让你更有共鸣，也能帮你更好理解这个岗位。"
)


def initialize_session(session: Session) -> str:
    session.conversation_history.append(
        {"role": "assistant", "content": GREETING}
    )
    return GREETING


async def process_message_stream(
    session: Session, user_message: str
) -> AsyncGenerator[dict, None]:
    session.touch()
    session.conversation_history.append({"role": "user", "content": user_message})

    messages = build_messages_for_chat(session)
    full_response = ""
    pending_buffer = ""
    in_extraction = False
    done_sent = False

    async for token in llm_client.chat_stream(messages):
        full_response += token

        if in_extraction:
            continue

        pending_buffer += token

        if "<" in pending_buffer:
            if "<extraction>" in pending_buffer:
                before_tag = pending_buffer.split("<extraction>")[0]
                if before_tag:
                    yield {"type": "token", "content": before_tag}
                in_extraction = True
                pending_buffer = ""

                # Immediately transition phase so skip-profile won't race
                if session.phase == Phase.JOB_COLLECTION:
                    session.phase = Phase.PROFILE_COLLECTION
                elif session.phase == Phase.PROFILE_COLLECTION:
                    session.phase = Phase.STORY_GENERATION

                yield {
                    "type": "done",
                    "phase": session.phase.value,
                    "phase_complete": True,
                    "transition_text": TRANSITION_TEXT if session.phase == Phase.PROFILE_COLLECTION else None,
                }
                done_sent = True

            elif not "<extraction>".startswith(pending_buffer[pending_buffer.rindex("<"):]):
                yield {"type": "token", "content": pending_buffer}
                pending_buffer = ""
        else:
            yield {"type": "token", "content": pending_buffer}
            pending_buffer = ""

    # Flush remaining buffer
    if pending_buffer and not in_extraction:
        clean = pending_buffer.split("<extraction>")[0] if "<extraction>" in pending_buffer else pending_buffer
        if clean:
            yield {"type": "token", "content": clean}

    # Parse extraction and update session state
    extraction = extract_tagged_json(full_response)
    visible_response = strip_extraction_tag(full_response)

    session.conversation_history.append(
        {"role": "assistant", "content": visible_response}
    )

    if extraction:
        if session.phase == Phase.PROFILE_COLLECTION:
            # Phase already transitioned; store extracted job data
            session.job_input = extraction
        elif session.phase == Phase.STORY_GENERATION:
            # Phase already transitioned; store extracted profile data
            session.user_profile = extraction.get("user_profile", extraction)

    # If no extraction was found, send a normal done event
    if not done_sent:
        yield {
            "type": "done",
            "phase": session.phase.value,
            "phase_complete": False,
            "transition_text": None,
        }


async def skip_profile(session: Session) -> str:
    session.touch()

    # Collect any user messages from profile phase as raw context (no LLM call)
    profile_user_msgs = [
        msg["content"] for msg in session.conversation_history
        if msg["role"] == "user"
    ]

    # If user answered at least one profile question, keep raw answers as context
    if len(profile_user_msgs) >= 2 and session.phase == Phase.PROFILE_COLLECTION:
        session.user_profile = {"raw_answers": profile_user_msgs[1:], "partial": True}
        session.profile_skipped = False
        session.phase = Phase.STORY_GENERATION
        return "好的，我已经记住了刚才聊到的部分～接下来我会根据已有的了解为你生成职业旅程。"

    session.profile_skipped = True
    session.phase = Phase.STORY_GENERATION
    return "好的，那我们直接出发吧～我会用一个比较通用的视角来为你生成这段职业旅程。"
