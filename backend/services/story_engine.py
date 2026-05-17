from typing import Generator

from models.user_state import UserState, Phase
from services.llm_client import llm_client
from services.prompt_engine import build_meta_intro_prompt, build_node_prompt, build_ending_prompt
from utils.json_extractor import extract_json_from_response
from utils.stream_extractor import StreamExtractor, MetaIntroStreamExtractor
from config import settings

NODE_SEQUENCE = [
    "intro", "node1", "node2", "node3",
    "taskAction", "taskEmotion", "taskDifficulty",
    "node4", "node5",
]


class StoryEngine:
    def generate_meta_and_intro(self, user_state: UserState) -> Generator[dict, None, None]:
        yield {"type": "progress", "message": "正在为你创建职业旅程..."}

        messages = build_meta_intro_prompt(user_state)
        full_response = ""
        extractor = MetaIntroStreamExtractor()

        try:
            for token in llm_client.chat_stream(
                messages, temperature=0.7, max_tokens=settings.max_tokens_node,
                username=user_state.username, session_id=user_state.session_id
            ):
                full_response += token
                for event in extractor.feed(full_response):
                    yield event
        except Exception as e:
            yield {"type": "error", "message": f"生成失败：{str(e)[:50]}，请重试"}
            return

        yield {"type": "stream_done"}

        result = extract_json_from_response(full_response)
        if not result:
            yield {"type": "progress", "message": "正在重新整理内容..."}
            result = self._retry_generation(messages, user_state.username, user_state.session_id)

        if result and self._validate_meta_intro(result):
            meta = result.get("meta", {})
            intro = result.get("intro", {})
            user_state.story_state.meta = meta
            user_state.story_state.generated_nodes["intro"] = intro
            user_state.story_state.current_node_id = "intro"
            yield {"type": "complete", "meta": meta, "node_id": "intro", "node": intro}
        else:
            yield {"type": "error", "message": "故事生成失败，请重试"}

    def generate_next_node(self, user_state: UserState, target_node_id: str) -> Generator[dict, None, None]:
        yield {"type": "progress", "message": "小可正在推进故事..."}

        messages = build_node_prompt(user_state, target_node_id)
        full_response = ""
        extractor = StreamExtractor()

        try:
            for token in llm_client.chat_stream(
                messages, temperature=0.7, max_tokens=settings.max_tokens_node,
                username=user_state.username, session_id=user_state.session_id
            ):
                full_response += token
                for event in extractor.feed(full_response):
                    yield event
        except Exception as e:
            yield {"type": "error", "message": f"生成失败：{str(e)[:50]}，请重试"}
            return

        yield {"type": "stream_done"}

        result = extract_json_from_response(full_response)
        if not result:
            yield {"type": "progress", "message": "正在重新整理内容..."}
            result = self._retry_generation(messages, user_state.username, user_state.session_id)

        node_data = result.get("node", result) if result else None

        if node_data and self._validate_node(node_data, target_node_id):
            user_state.story_state.generated_nodes[target_node_id] = node_data
            user_state.story_state.current_node_id = target_node_id
            yield {"type": "complete", "node_id": target_node_id, "node": node_data}
        else:
            yield {"type": "error", "message": "节点生成失败，请重试"}

    def generate_ending(self, user_state: UserState) -> Generator[dict, None, None]:
        yield {"type": "progress", "message": "正在生成结局..."}

        messages = build_ending_prompt(user_state)
        full_response = ""
        extractor = StreamExtractor()

        try:
            for token in llm_client.chat_stream(
                messages, temperature=0.7, max_tokens=settings.max_tokens_ending,
                username=user_state.username, session_id=user_state.session_id
            ):
                full_response += token
                for event in extractor.feed(full_response):
                    yield event
        except Exception as e:
            yield {"type": "error", "message": f"生成失败：{str(e)[:50]}，请重试"}
            return

        yield {"type": "stream_done"}

        result = extract_json_from_response(full_response)
        if not result:
            yield {"type": "progress", "message": "正在重新整理内容..."}
            result = self._retry_generation(messages, user_state.username, user_state.session_id)

        if result and self._validate_ending(result):
            user_state.story_state.generated_nodes["ending"] = result
            user_state.phase = Phase.COMPLETED
            scores = user_state.story_state.scores
            fit = scores.get("fit", 0)
            bucket = "high" if fit >= 9 else ("mid" if fit >= 3 else "low")
            yield {"type": "ending", "ending": result, "bucket": bucket, "scores": scores}
        else:
            yield {"type": "error", "message": "结局生成失败，请重试"}

    def _retry_generation(self, messages: list[dict], username: str, session_id: str = None):
        try:
            full_response = ""
            for token in llm_client.chat_stream(
                messages, temperature=0.5, max_tokens=settings.max_tokens_node,
                username=username, session_id=session_id
            ):
                full_response += token
            return extract_json_from_response(full_response)
        except Exception:
            return None

    def _validate_meta_intro(self, result: dict) -> bool:
        if not isinstance(result, dict):
            return False
        if "meta" not in result or "intro" not in result:
            return False
        meta = result["meta"]
        if not all(k in meta for k in ("title", "description")):
            return False
        intro = result["intro"]
        return self._validate_node(intro, "intro")

    def _validate_node(self, node: dict, node_id: str) -> bool:
        if not isinstance(node, dict):
            return False
        if "paragraphs" not in node or "options" not in node:
            return False
        if not isinstance(node["options"], list) or len(node["options"]) == 0:
            return False
        for opt in node["options"]:
            if "key" not in opt or "label" not in opt or "next" not in opt:
                return False
        return True

    def _validate_ending(self, result: dict) -> bool:
        if not isinstance(result, dict):
            return False
        return "title" in result and "paragraphs" in result


story_engine = StoryEngine()
