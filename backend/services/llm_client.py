import time
from typing import Generator

import httpx
from openai import OpenAI

from config import settings
from services.persistence import persistence
from utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.client = None
        self.model = ""
        self.provider_name = ""
        self.refresh_from_settings()

    def refresh_from_settings(self):
        self.client = OpenAI(
            base_url=settings.active_base_url,
            api_key=settings.active_api_key,
            timeout=httpx.Timeout(90.0, connect=10.0),
        )
        self.model = settings.model_name
        self.provider_name = settings.provider_name

    def _request_kwargs(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> dict:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if self.provider_name == "deepseek":
            if settings.reasoning_effort:
                kwargs["reasoning_effort"] = settings.reasoning_effort
            if settings.thinking_type:
                kwargs["extra_body"] = {"thinking": {"type": settings.thinking_type}}

        return kwargs

    def chat(
        self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 2048,
        username: str = None
    ) -> str:
        start = time.time()
        logger.info("llm chat start user=%s provider=%s model=%s", username or "anonymous", self.provider_name, self.model)
        resp = self.client.chat.completions.create(**self._request_kwargs(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        ))
        content = resp.choices[0].message.content
        if username:
            persistence.append_llm_log(username, {
                "purpose": "chat",
                "provider": self.provider_name,
                "model": self.model,
                "messages_sent": messages,
                "response": content,
                "duration_ms": int((time.time() - start) * 1000),
            })
        logger.info("llm chat complete user=%s duration_ms=%s", username or "anonymous", int((time.time() - start) * 1000))
        return content

    def chat_stream(
        self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 2048,
        username: str = None
    ) -> Generator[str, None, None]:
        start = time.time()
        logger.info("llm stream start user=%s provider=%s model=%s", username or "anonymous", self.provider_name, self.model)
        stream = self.client.chat.completions.create(**self._request_kwargs(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        ))
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response += token
                yield token
        if username:
            persistence.append_llm_log(username, {
                "purpose": "chat_stream",
                "provider": self.provider_name,
                "model": self.model,
                "messages_sent": messages,
                "response": full_response,
                "duration_ms": int((time.time() - start) * 1000),
            })
        logger.info(
            "llm stream complete user=%s duration_ms=%s chars=%s",
            username or "anonymous",
            int((time.time() - start) * 1000),
            len(full_response),
        )


llm_client = LLMClient()
