import os
import yaml

BASE_DIR = os.path.dirname(__file__)


class Settings:
    def __init__(self):
        self.loaded = False

        self.provider_name = "xi"

        self.xi_api_key = ""
        self.xi_api_base_url = "https://api.xi-ai.cn/v1"

        self.deepseek_api_key = ""
        self.deepseek_api_base_url = "https://api.deepseek.com"

        self.model_name = "deepseek-v4-pro"
        self.reasoning_effort = ""
        self.thinking_type = ""

        self.max_tokens_chat = 2048
        self.max_tokens_node = 4096
        self.max_tokens_ending = 2048

        self.data_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "users"))
        self.cors_origins = ["*"]

        self.host = "0.0.0.0"
        self.port = 8000
        self.debug = True

    def load_from_yaml(self, config_path: str) -> None:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self.provider_name = data.get("provider_name", self.provider_name)
        self.xi_api_base_url = data.get("xi_api_base_url", self.xi_api_base_url)
        self.deepseek_api_base_url = data.get("deepseek_api_base_url", self.deepseek_api_base_url)
        self.model_name = data.get("model_name", self.model_name)
        self.reasoning_effort = data.get("reasoning_effort", self.reasoning_effort)
        self.thinking_type = data.get("thinking_type", self.thinking_type)

        self.max_tokens_chat = data.get("max_tokens_chat", self.max_tokens_chat)
        self.max_tokens_node = data.get("max_tokens_node", self.max_tokens_node)
        self.max_tokens_ending = data.get("max_tokens_ending", self.max_tokens_ending)

        raw_data_dir = data.get("data_dir", self.data_dir)
        if os.path.isabs(raw_data_dir):
            self.data_dir = raw_data_dir
        else:
            self.data_dir = os.path.abspath(os.path.join(os.path.dirname(config_path), raw_data_dir))

        self.cors_origins = data.get("cors_origins", self.cors_origins)
        self.host = data.get("host", self.host)
        self.port = data.get("port", self.port)
        self.debug = data.get("debug", self.debug)
        self.loaded = True

    def apply_cli_overrides(
        self,
        provider_name: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        reasoning_effort: str | None = None,
        thinking_type: str | None = None,
        host: str | None = None,
        port: int | None = None,
        debug: bool | None = None,
    ) -> None:
        if provider_name:
            self.provider_name = provider_name

        if base_url:
            if self.provider_name == "deepseek":
                self.deepseek_api_base_url = base_url
            else:
                self.xi_api_base_url = base_url

        if model_name:
            self.model_name = model_name

        if reasoning_effort is not None:
            self.reasoning_effort = reasoning_effort

        if thinking_type is not None:
            self.thinking_type = thinking_type

        if host:
            self.host = host

        if port is not None:
            self.port = port

        if debug is not None:
            self.debug = debug

    def load_api_keys_or_raise(self) -> None:
        self.xi_api_key = os.getenv("XI_API_KEY", "").strip()
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

        if self.provider_name == "xi" and not self.xi_api_key:
            raise RuntimeError("缺少环境变量 XI_API_KEY，程序退出。")
        if self.provider_name == "deepseek" and not self.deepseek_api_key:
            raise RuntimeError("缺少环境变量 DEEPSEEK_API_KEY，程序退出。")
        if self.provider_name not in {"xi", "deepseek"}:
            raise RuntimeError(f"不支持的 provider: {self.provider_name}")

    @property
    def active_base_url(self) -> str:
        if self.provider_name == "deepseek":
            return self.deepseek_api_base_url
        return self.xi_api_base_url

    @property
    def active_api_key(self) -> str:
        if self.provider_name == "deepseek":
            return self.deepseek_api_key
        return self.xi_api_key


settings = Settings()
