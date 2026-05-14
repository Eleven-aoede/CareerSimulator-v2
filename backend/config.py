import os


class Settings:
    xi_api_key: str = os.environ.get("XI_API_KEY", "")
    xi_api_base_url: str = "https://api.xi-ai.cn/v1"
    model_name: str = "deepseek-v4-pro"

    session_ttl_seconds: int = 3600
    max_conversation_turns: int = 30
    max_tokens_chat: int = 2048
    max_tokens_story: int = 8192

    cors_origins: list[str] = ["*"]


settings = Settings()
