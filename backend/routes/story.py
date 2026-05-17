import json
from flask import Blueprint, request, Response, jsonify

from services.persistence import persistence
from services.story_engine import story_engine
from models.user_state import Phase
from utils.logger import get_logger

story_bp = Blueprint("story", __name__)
logger = get_logger(__name__)

NODE_SEQUENCE = [
    "intro", "node1", "node2", "node3",
    "taskAction", "taskEmotion", "taskDifficulty",
    "node4", "node5",
]


@story_bp.route("/users/<username>/sessions/<session_id>/story/next-node", methods=["POST"])
def next_node(username: str, session_id: str):
    if not persistence.session_exists(username, session_id):
        return jsonify({"error": "会话不存在"}), 404

    user_state = persistence.load_state(username, session_id)
    data = request.get_json()
    action = data.get("action")
    choice_key = data.get("choice_key")
    current_node = data.get("current_node")

    if action == "start":
        if user_state.phase != Phase.STORY_SIMULATION:
            return jsonify({"error": "尚未完成信息收集"}), 400

        def gen_start():
            success = False
            logger.info("story start username=%s session=%s", username, session_id)
            for event in story_engine.generate_meta_and_intro(user_state):
                if event.get("type") == "complete":
                    success = True
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if success:
                persistence.save_state(user_state, session_id)
                persistence.append_system_log(username, session_id, {"event": "story_started"})

        return Response(gen_start(), mimetype="text/event-stream", headers=_sse_headers())

    if choice_key and current_node:
        if user_state.phase != Phase.STORY_SIMULATION:
            return jsonify({"error": "当前阶段不支持故事推进"}), 400

        current_node_data = user_state.story_state.generated_nodes.get(current_node, {})
        options = current_node_data.get("options", [])
        chosen_option = next((o for o in options if o["key"] == choice_key), None)

        if not chosen_option:
            return jsonify({"error": "无效的选项"}), 400

        choice_label = chosen_option.get("label", "")
        effect = chosen_option.get("effect", {})
        next_node_id = chosen_option.get("next", "")

        user_state.story_state.choices.append({
            "node_id": current_node,
            "choice_key": choice_key,
            "choice_label": choice_label,
            "effect": effect,
        })
        for k in ("fit", "stress", "growth"):
            user_state.story_state.scores[k] += effect.get(k, 0)

        logger.info("story choice username=%s session=%s node=%s choice=%s", username, session_id, current_node, choice_key)

        if next_node_id == "__ENDING__":
            def gen_ending():
                success = False
                for event in story_engine.generate_ending(user_state):
                    if event.get("type") == "ending":
                        success = True
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if success:
                    persistence.save_state(user_state, session_id)
                    persistence.append_history(username, session_id, {
                        "type": "story_choice",
                        "node_id": current_node,
                        "choice_key": choice_key,
                        "choice_label": choice_label,
                    })
                    persistence.append_system_log(username, session_id, {
                        "event": "story_choice",
                        "node_id": current_node,
                        "choice_key": choice_key,
                    })
                    persistence.append_system_log(username, session_id, {"event": "story_completed"})

            return Response(gen_ending(), mimetype="text/event-stream", headers=_sse_headers())
        else:
            def gen_node():
                success = False
                for event in story_engine.generate_next_node(user_state, next_node_id):
                    if event.get("type") == "complete":
                        success = True
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if success:
                    persistence.save_state(user_state, session_id)
                    persistence.append_history(username, session_id, {
                        "type": "story_choice",
                        "node_id": current_node,
                        "choice_key": choice_key,
                        "choice_label": choice_label,
                    })
                    persistence.append_system_log(username, session_id, {
                        "event": "story_choice",
                        "node_id": current_node,
                        "choice_key": choice_key,
                    })
                    persistence.append_system_log(username, session_id, {
                        "event": "node_generated",
                        "node_id": next_node_id,
                    })

            return Response(gen_node(), mimetype="text/event-stream", headers=_sse_headers())

    return jsonify({"error": "请提供 action 或 choice_key + current_node"}), 400


def _sse_headers():
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
