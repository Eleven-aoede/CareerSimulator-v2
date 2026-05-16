import json
import os

from agents.base import BaseAgent
from models.user_state import Phase, UserState

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def _read_prompt(filename: str) -> str:
    with open(os.path.join(PROMPTS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


class XiaoKeAgent(BaseAgent):
    name = "xiaoke"

    def build_chat_system_prompt(self, user_state: UserState) -> str:
        base = _read_prompt("xiaoke_base.md")

        if user_state.phase == Phase.JOB_COLLECTION:
            return f"{base}\n\n{_read_prompt('phase_job.md')}"

        if user_state.phase == Phase.PROFILE_COLLECTION:
            phase_prompt = _read_prompt("phase_profile.md")
            job_context = json.dumps(user_state.job_input or {}, ensure_ascii=False, indent=2)
            return f"{base}\n\n{phase_prompt.replace('{job_input_context}', job_context)}"

        return base
