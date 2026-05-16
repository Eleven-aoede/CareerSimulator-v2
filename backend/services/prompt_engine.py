import json
import os

from agents.registry import agent_registry
from models.user_state import UserState

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def _read_prompt(filename: str) -> str:
    with open(os.path.join(PROMPTS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def build_system_prompt(user_state: UserState) -> str:
    return agent_registry.get("xiaoke").build_chat_system_prompt(user_state)


def build_messages_for_chat(user_state: UserState) -> list[dict]:
    system_prompt = build_system_prompt(user_state)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(user_state.conversation_history)
    return messages


def build_meta_intro_prompt(user_state: UserState) -> list[dict]:
    prompt_template = _read_prompt("story_meta.md")
    input_payload = {
        "version": "ifi-profile-input-v1",
        "profile_skipped": user_state.profile_skipped,
        "job_input": user_state.job_input or {},
        "user_profile": user_state.user_profile or {},
    }
    input_json = json.dumps(input_payload, ensure_ascii=False, indent=2)
    prompt = prompt_template.replace("{input_json}", input_json)
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "请根据以上信息生成 meta 和 intro 节点的 JSON。"},
    ]


def build_node_prompt(user_state: UserState, target_node_id: str) -> list[dict]:
    prompt_template = _read_prompt("story_node.md")

    input_payload = {
        "job_input": user_state.job_input or {},
        "user_profile": user_state.user_profile or {},
    }

    narrative_context = []
    for choice in user_state.story_state.choices:
        node_id = choice["node_id"]
        node_data = user_state.story_state.generated_nodes.get(node_id, {})
        narrative_context.append({
            "node_id": node_id,
            "title": node_data.get("title", ""),
            "paragraphs_summary": node_data.get("paragraphs", [""])[0][:100],
            "choice_made": choice.get("choice_label", ""),
            "choice_key": choice.get("choice_key", ""),
        })

    node_format_ref = _read_prompt("references/story-node-format.md")
    option_ref = _read_prompt("references/option-generation.md")

    prompt = prompt_template.replace("{input_json}", json.dumps(input_payload, ensure_ascii=False, indent=2))
    prompt = prompt.replace("{node_id}", target_node_id)
    prompt = prompt.replace("{narrative_context}", json.dumps(narrative_context, ensure_ascii=False, indent=2))
    prompt = prompt.replace("{accumulated_scores}", json.dumps(user_state.story_state.scores, ensure_ascii=False))
    prompt = prompt.replace("{node_format_reference}", node_format_ref)
    prompt = prompt.replace("{option_reference}", option_ref)

    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"请生成 {target_node_id} 节点的 JSON。"},
    ]


def build_ending_prompt(user_state: UserState) -> list[dict]:
    prompt_template = _read_prompt("story_ending.md")

    scores = user_state.story_state.scores
    fit = scores.get("fit", 0)
    if fit >= 9:
        ending_bucket = "high"
    elif fit >= 3:
        ending_bucket = "mid"
    else:
        ending_bucket = "low"

    narrative_summary = []
    for choice in user_state.story_state.choices:
        node_id = choice["node_id"]
        node_data = user_state.story_state.generated_nodes.get(node_id, {})
        narrative_summary.append({
            "node_id": node_id,
            "title": node_data.get("title", ""),
            "choice": choice.get("choice_label", ""),
        })

    task_recap = {}
    for nid in ["taskAction", "taskEmotion", "taskDifficulty"]:
        for choice in user_state.story_state.choices:
            if choice["node_id"] == nid:
                task_recap[nid] = choice.get("choice_label", "")

    input_payload = {
        "job_input": user_state.job_input or {},
        "user_profile": user_state.user_profile or {},
    }

    prompt = prompt_template.replace("{input_json}", json.dumps(input_payload, ensure_ascii=False, indent=2))
    prompt = prompt.replace("{narrative_summary}", json.dumps(narrative_summary, ensure_ascii=False, indent=2))
    prompt = prompt.replace("{accumulated_scores}", json.dumps(scores, ensure_ascii=False))
    prompt = prompt.replace("{ending_bucket}", ending_bucket)
    prompt = prompt.replace("{task_recap}", json.dumps(task_recap, ensure_ascii=False, indent=2))

    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"请生成 {ending_bucket} 等级的结局 JSON。"},
    ]
