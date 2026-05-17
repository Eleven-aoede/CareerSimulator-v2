import os
import secrets

from flask import Blueprint, request, jsonify

from services.persistence import persistence

admin_bp = Blueprint("admin_bp", __name__)

_ADMIN_KEY = os.environ.get("IFI_Career_Simulator_KEY", "")
_active_tokens: dict[str, bool] = {}


def _check_token() -> bool:
    token = request.headers.get("X-Admin-Token", "")
    return token in _active_tokens


@admin_bp.route("/admin/auth", methods=["POST"])
def admin_auth():
    body = request.get_json(silent=True) or {}
    key = body.get("key", "")
    if not _ADMIN_KEY or key != _ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 401
    token = secrets.token_hex(16)
    _active_tokens[token] = True
    return jsonify({"status": "ok", "token": token})


@admin_bp.route("/admin/users", methods=["GET"])
def admin_list_users():
    if not _check_token():
        return jsonify({"error": "unauthorized"}), 401
    users = persistence.list_users()
    return jsonify(users)


@admin_bp.route("/admin/users/<username>/sessions", methods=["GET"])
def admin_user_sessions(username):
    if not _check_token():
        return jsonify({"error": "unauthorized"}), 401
    if not persistence.user_exists(username):
        return jsonify({"error": "user not found"}), 404
    sessions = persistence.list_sessions(username)
    return jsonify(sessions)


@admin_bp.route("/admin/users/<username>/sessions/<session_id>/state", methods=["GET"])
def admin_user_state(username, session_id):
    if not _check_token():
        return jsonify({"error": "unauthorized"}), 401
    if not persistence.session_exists(username, session_id):
        return jsonify({"error": "session not found"}), 404
    user_state = persistence.load_state(username, session_id)
    return jsonify(user_state.to_dict())


@admin_bp.route("/admin/users/<username>/sessions/<session_id>/conversation", methods=["GET"])
def admin_user_conversation(username, session_id):
    if not _check_token():
        return jsonify({"error": "unauthorized"}), 401
    if not persistence.session_exists(username, session_id):
        return jsonify({"error": "session not found"}), 404
    user_state = persistence.load_state(username, session_id)
    return jsonify(user_state.conversation_history)


@admin_bp.route("/admin/users/<username>/sessions/<session_id>/llm-log", methods=["GET"])
def admin_user_llm_log(username, session_id):
    if not _check_token():
        return jsonify({"error": "unauthorized"}), 401
    logs = persistence.load_llm_log(username, session_id)
    return jsonify(logs)


@admin_bp.route("/admin/users/<username>/sessions/<session_id>/system-log", methods=["GET"])
def admin_user_system_log(username, session_id):
    if not _check_token():
        return jsonify({"error": "unauthorized"}), 401
    logs = persistence.load_system_log(username, session_id)
    return jsonify(logs)
