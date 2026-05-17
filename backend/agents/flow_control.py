import json
import os
import re

from services.llm_client import llm_client
from models.user_state import UserState, Phase
from utils.logger import get_logger

logger = get_logger(__name__)
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def _read_prompt(filename: str) -> str:
    with open(os.path.join(PROMPTS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


class FlowControlAgent:
    def evaluate(self, user_state: UserState) -> dict:
        phase = user_state.phase
        if phase == Phase.JOB_COLLECTION:
            system_prompt = _read_prompt("flow_control_job.md")
        elif phase == Phase.PROFILE_COLLECTION:
            system_prompt = _read_prompt("flow_control_profile.md")
        else:
            return {"should_advance": False}

        user_messages = [
            m["content"] for m in user_state.conversation_history if m["role"] == "user"
        ]
        latest_assistant = ""
        for m in reversed(user_state.conversation_history):
            if m["role"] == "assistant":
                latest_assistant = m["content"]
                break

        input_text = (
            "## 当前阶段所有用户消息\n"
            + "\n---\n".join(user_messages)
            + "\n\n## xiaoke 最新回复\n"
            + latest_assistant
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text},
        ]

        response = llm_client.chat(
            messages, temperature=0.2, max_tokens=1024, username=user_state.username
        )
        return self._parse_response(response)

    def _parse_response(self, response: str) -> dict:
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        logger.warning("flow-control parse failed: %s", response[:200])
        return {"should_advance": False}


flow_control = FlowControlAgent()
