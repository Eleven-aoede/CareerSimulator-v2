from flask import Blueprint, request, jsonify

from services.persistence import persistence
from services.conversation import initialize_session
from models.user_state import UserState
from utils.logger import get_logger

user_bp = Blueprint("user", __name__)
logger = get_logger(__name__)


@user_bp.route("/users", methods=["POST"])
def create_or_check_user():
    data = request.get_json()
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "用户名不能为空"}), 400

    if persistence.user_exists(username):
        user_state = persistence.load_state(username)
        logger.info("user exists username=%s phase=%s", username, user_state.phase.value)
        return jsonify({
            "status": "exists",
            "username": username,
            "phase": user_state.phase.value,
            "last_active": user_state.last_active,
            "current_node": user_state.story_state.current_node_id,
        })

    user_state = UserState(username=username)
    greeting = initialize_session(user_state)
    persistence.save_state(user_state)
    persistence.append_system_log(username, {"event": "user_created"})
    logger.info("user created username=%s", username)

    return jsonify({
        "status": "new",
        "username": username,
        "phase": user_state.phase.value,
        "greeting": greeting,
    })


@user_bp.route("/users/<username>/reset", methods=["POST"])
def reset_user(username: str):
    persistence.clear_user(username)
    user_state = UserState(username=username)
    greeting = initialize_session(user_state)
    persistence.save_state(user_state)
    persistence.append_system_log(username, {"event": "user_reset"})
    logger.info("user reset username=%s", username)

    return jsonify({
        "status": "reset",
        "username": username,
        "phase": user_state.phase.value,
        "greeting": greeting,
    })


@user_bp.route("/users/<username>/state", methods=["GET"])
def get_user_state(username: str):
    if not persistence.user_exists(username):
        return jsonify({"error": "用户不存在"}), 404

    user_state = persistence.load_state(username)
    logger.info("state fetched username=%s phase=%s", username, user_state.phase.value)
    return jsonify(user_state.to_dict())
