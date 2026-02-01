from __future__ import annotations
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        """Return a JSON string (not markdown) that conforms to schema."""
        raise NotImplementedError
