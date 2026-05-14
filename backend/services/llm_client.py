import httpx
from openai import AsyncOpenAI
from typing import AsyncGenerator

from config import settings


class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=settings.xi_api_base_url,
            api_key=settings.xi_api_key,
            timeout=httpx.Timeout(180.0, connect=10.0),
        )
        self.model = settings.model_name

    async def chat(
        self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 2048
    ) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

    async def chat_stream(
        self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


llm_client = LLMClient()
