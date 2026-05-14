import json
import os

from models.session import Session, Phase

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def _read_prompt(filename: str) -> str:
    with open(os.path.join(PROMPTS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def build_system_prompt(session: Session) -> str:
    base = _read_prompt("xiaoke_base.md")

    if session.phase == Phase.JOB_COLLECTION:
        phase_prompt = _read_prompt("phase_job.md")
        return f"{base}\n\n{phase_prompt}"

    elif session.phase == Phase.PROFILE_COLLECTION:
        phase_prompt = _read_prompt("phase_profile.md")
        job_context = json.dumps(session.job_input, ensure_ascii=False, indent=2)
        phase_prompt = phase_prompt.replace("{job_input_context}", job_context)
        return f"{base}\n\n{phase_prompt}"

    elif session.phase == Phase.STORY_GENERATION:
        return _build_story_prompt(session)

    return base


def _build_story_prompt(session: Session) -> str:
    phase_prompt = _read_prompt("phase_story.md")

    input_payload = {
        "version": "ifi-profile-input-v1",
        "profile_skipped": session.profile_skipped,
        "job_input": session.job_input or {},
        "user_profile": session.user_profile or {},
    }
    input_json = json.dumps(input_payload, ensure_ascii=False, indent=2)
    phase_prompt = phase_prompt.replace("{input_json}", input_json)

    return phase_prompt


def build_messages_for_chat(session: Session) -> list[dict]:
    system_prompt = build_system_prompt(session)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(session.conversation_history)
    return messages


def build_messages_for_story(session: Session) -> list[dict]:
    system_prompt = _build_story_prompt(session)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请根据以上输入生成完整的职业模拟交互脚本 JSON。"},
    ]
    return messages
