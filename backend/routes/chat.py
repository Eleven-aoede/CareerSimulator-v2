import json
from flask import Blueprint, request, Response, jsonify

from services.persistence import persistence
from services.conversation import process_message_stream, skip_profile
from models.user_state import Phase
from utils.logger import get_logger

chat_bp = Blueprint("chat", __name__)
logger = get_logger(__name__)


@chat_bp.route("/users/<username>/sessions/<session_id>/chat/stream", methods=["POST"])
def chat_stream(username: str, session_id: str):
    if not persistence.session_exists(username, session_id):
        return jsonify({"error": "会话不存在"}), 404

    user_state = persistence.load_state(username, session_id)
    if user_state.phase not in (Phase.JOB_COLLECTION, Phase.PROFILE_COLLECTION):
        return jsonify({"error": "当前阶段不支持聊天"}), 400

    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    initial_phase = user_state.phase
    persistence.append_history(username, session_id, {"type": "chat", "role": "user", "content": message})
    logger.info("chat stream start username=%s session=%s phase=%s", username, session_id, user_state.phase.value)

    def event_generator():
        state_saved = False
        for event in process_message_stream(user_state, message):
            if event.get("phase_complete") and not state_saved:
                persistence.save_state(user_state, session_id)
                state_saved = True
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        if not state_saved:
            persistence.save_state(user_state, session_id)
        persistence.append_history(username, session_id, {
            "type": "chat",
            "role": "assistant",
            "content": user_state.conversation_history[-1]["content"] if user_state.conversation_history else "",
        })
        if user_state.phase != initial_phase:
            persistence.append_system_log(username, session_id, {
                "event": "phase_updated",
                "phase": user_state.phase.value,
            })
        logger.info("chat stream complete username=%s session=%s phase=%s", username, session_id, user_state.phase.value)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@chat_bp.route("/users/<username>/sessions/<session_id>/skip-profile", methods=["POST"])
def skip_profile_route(username: str, session_id: str):
    if not persistence.session_exists(username, session_id):
        return jsonify({"error": "会话不存在"}), 404

    user_state = persistence.load_state(username, session_id)
    message = skip_profile(user_state)
    user_state.conversation_history.append({"role": "assistant", "content": message})
    persistence.save_state(user_state, session_id)
    persistence.append_history(username, session_id, {"type": "chat", "role": "assistant", "content": message})
    persistence.append_system_log(username, session_id, {"event": "profile_skipped"})
    logger.info("profile skipped username=%s session=%s", username, session_id)

    return jsonify({
        "phase": user_state.phase.value,
        "message": message,
    })
