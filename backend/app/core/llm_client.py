"""Unified LLM client with retry support."""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.retry import llm_retry


class LLMClient:
    """Thin wrapper around AsyncOpenAI providing a simple ``call()`` interface.

    This eliminates the repeated pattern of building messages,
    calling ``chat.completions.create``, and extracting content
    across 6+ call sites.
    """

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @llm_retry
    async def call(
        self,
        system_prompt: str,
        user_msg: str,
        temperature: float = 0.1,
        messages: list[dict] | None = None,
    ) -> str:
        """Send a single turn to the LLM and return the content string.

        Args:
            system_prompt: System message content.
            user_msg: User message content.
            temperature: Sampling temperature (0.0-1.0).
            messages: If provided, use this full message list instead of
                constructing [system, user].  Useful when the caller needs
                to inject history or other context.
        """
        if messages is None:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ]
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
