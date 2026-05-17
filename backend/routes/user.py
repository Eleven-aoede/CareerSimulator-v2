from flask import Blueprint, request, jsonify

from services.persistence import persistence
from services.conversation import initialize_session
from models.user_state import UserState
from utils.logger import get_logger

user_bp = Blueprint("user", __name__)
logger = get_logger(__name__)


@user_bp.route("/users", methods=["POST"])
def check_user():
    data = request.get_json()
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "用户名不能为空"}), 400

    if not persistence.user_exists(username):
        session_id = persistence.create_session(username)
        user_state = UserState(username=username, session_id=session_id)
        greeting = initialize_session(user_state)
        persistence.save_state(user_state, session_id)
        persistence.append_system_log(username, session_id, {"event": "user_created"})
        logger.info("user created username=%s session=%s", username, session_id)
        return jsonify({
            "status": "new",
            "username": username,
            "session_id": session_id,
            "phase": user_state.phase.value,
            "greeting": greeting,
        })

    sessions = persistence.list_sessions(username)
    logger.info("user exists username=%s sessions=%d", username, len(sessions))
    return jsonify({
        "status": "exists",
        "username": username,
        "sessions": sessions,
    })


@user_bp.route("/users/<username>/sessions", methods=["POST"])
def create_session(username: str):
    session_id = persistence.create_session(username)
    user_state = UserState(username=username, session_id=session_id)
    greeting = initialize_session(user_state)
    persistence.save_state(user_state, session_id)
    persistence.append_system_log(username, session_id, {"event": "session_created"})
    logger.info("session created username=%s session=%s", username, session_id)

    return jsonify({
        "status": "new",
        "username": username,
        "session_id": session_id,
        "phase": user_state.phase.value,
        "greeting": greeting,
    })


@user_bp.route("/users/<username>/sessions/<session_id>/load", methods=["POST"])
def load_session(username: str, session_id: str):
    if not persistence.session_exists(username, session_id):
        return jsonify({"error": "会话不存在"}), 404

    user_state = persistence.load_state(username, session_id)
    logger.info("session loaded username=%s session=%s phase=%s", username, session_id, user_state.phase.value)
    return jsonify({
        "status": "loaded",
        "session_id": session_id,
        **user_state.to_dict(),
    })


@user_bp.route("/users/<username>/sessions/<session_id>/reset", methods=["POST"])
def reset_session(username: str, session_id: str):
    persistence.delete_session(username, session_id)
    new_session_id = persistence.create_session(username)
    user_state = UserState(username=username, session_id=new_session_id)
    greeting = initialize_session(user_state)
    persistence.save_state(user_state, new_session_id)
    persistence.append_system_log(username, new_session_id, {"event": "session_reset"})
    logger.info("session reset username=%s old=%s new=%s", username, session_id, new_session_id)

    return jsonify({
        "status": "reset",
        "username": username,
        "session_id": new_session_id,
        "phase": user_state.phase.value,
        "greeting": greeting,
    })
