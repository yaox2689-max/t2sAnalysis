"""Retry decorators for external API calls."""

from __future__ import annotations

from openai import APIConnectionError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (APIConnectionError, APITimeoutError, RateLimitError)
    ),
    reraise=True,
)
"""Retry decorator for LLM API calls.

Retries up to 3 times with exponential backoff on connection errors,
timeouts, and rate limit errors.
"""
