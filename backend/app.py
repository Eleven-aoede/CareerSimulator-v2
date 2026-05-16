import os
import argparse
import sys
from flask import Flask, send_from_directory
from flask_cors import CORS

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def default_config_path() -> str:
    return os.path.join(os.path.dirname(__file__), "config.yaml")


def bootstrap_settings(args=None) -> None:
    settings.load_from_yaml(default_config_path())

    debug_override = None
    if args is not None:
        if args.debug:
            debug_override = True
        if args.no_debug:
            debug_override = False

        settings.apply_cli_overrides(
            provider_name=args.provider,
            base_url=args.base_url,
            model_name=args.model,
            reasoning_effort=args.reasoning_effort,
            thinking_type=args.thinking_type,
            host=args.host,
            port=args.port,
            debug=debug_override,
        )

    settings.load_api_keys_or_raise()


def create_app():
    if not settings.loaded:
        bootstrap_settings()

    app = Flask(__name__)
    CORS(app, origins=settings.cors_origins)

    from routes.user import user_bp
    from routes.chat import chat_bp
    from routes.story import story_bp
    from routes.admin import admin_bp

    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(story_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")

    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

    @app.route("/")
    def serve_index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/<path:path>")
    def serve_static(path):
        return send_from_directory(frontend_dir, path)

    logger.info("app created frontend_dir=%s", frontend_dir)
    return app


def parse_args():
    parser = argparse.ArgumentParser(description="IFI Career Simulator backend")
    parser.add_argument("--provider", choices=["xi", "deepseek"], help="模型提供商")
    parser.add_argument("--base-url", help="模型接口 base_url")
    parser.add_argument("--model", help="模型名称")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"], help="推理强度")
    parser.add_argument("--thinking-type", choices=["enabled", "disabled"], help="是否启用 thinking")
    parser.add_argument("--host", help="Flask 启动 host")
    parser.add_argument("--port", type=int, help="Flask 启动端口")
    parser.add_argument("--debug", action="store_true", help="启用 Flask debug")
    parser.add_argument("--no-debug", action="store_true", help="关闭 Flask debug")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        bootstrap_settings(args)
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)

    logger.info(
        "startup config provider=%s model=%s base_url=%s host=%s port=%s debug=%s",
        settings.provider_name,
        settings.model_name,
        settings.active_base_url,
        settings.host,
        settings.port,
        settings.debug,
    )
    app = create_app()
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
