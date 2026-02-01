from __future__ import annotations
import json
import os
import sys
import httpx
from spec2ir.llm.base import LLMProvider



_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


class OpenAICompatProvider(LLMProvider):
    """OpenAI-compatible Chat Completions client.
    Works with OpenAI, Azure OpenAI (if compatible gateway), or internal gateways exposing /v1/chat/completions.
    Configure via env:
      - LLM_BASE_URL (default: https://api.openai.com/v1)
      - LLM_API_KEY (required)
      - LLM_MODEL (default: gpt-4.1-mini; change to your gateway model)
      - LLM_TIMEOUT_SEC (default: 60)
      - LLM_STREAM (default: disabled; set to 1/true to stream tokens to stdout)
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "gpt-4.1-mini")
        self.timeout = float(os.getenv("LLM_TIMEOUT_SEC", "60"))
        self.stream = _env_flag("LLM_STREAM", False)

        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is required for OpenAICompatProvider")

    async def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.stream:
            payload["stream"] = True

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if self.stream:
                return await self._stream_completion(client, url, headers, payload)
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    async def _stream_completion(self, client, url: str, headers: dict, payload: dict) -> str:
        chunks: list[str] = []
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[len("data: "):].strip()
                if not data_str:
                    continue
                if data_str == "[DONE]":
                    break
                try:
                    payload_json = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                delta = payload_json.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    sys.stdout.write(content)
                    sys.stdout.flush()
                    chunks.append(content)
        if chunks:
            sys.stdout.write("\n")
            sys.stdout.flush()
        return ''.join(chunks)
