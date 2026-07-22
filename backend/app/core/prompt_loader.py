"""PromptLoader — unified Prompt loading, caching, and variable substitution.

Usage:
    from app.core.prompt_loader import prompt_loader

    prompt = prompt_loader.load("sql_agent/sql_generation",
                                task_type="trend",
                                schema="...")
    if prompt_loader.exists("tools/chart"):
        ...
    prompt_loader.clear_cache()
"""

import os
from typing import Optional

_PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "prompts")


class PromptNotFoundError(FileNotFoundError):
    """Raised when a prompt file does not exist."""


class PromptLoader:
    """Load, cache, and render prompt Markdown files.

    Prompts are stored under ``backend/prompts/<name>.md`` where *name*
    is a forward-slash-separated path, e.g. ``"sql_agent/sql_generation"``.
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self._base_dir = base_dir or _PROMPT_DIR
        self._cache: dict[str, str] = {}

    def load(self, name: str, **variables: object) -> str:
        """Load a prompt file by its dotted name, optionally substitute variables.

        Variable substitution uses ``str.replace`` for ``{{ var }}`` placeholders.
        No template engine dependency required.

        Raises:
            PromptNotFoundError: if the prompt file does not exist.
        """
        content = self._load_raw(name)
        if not variables:
            return content

        for key, value in variables.items():
            placeholder = "{{ " + key + " }}"
            content = content.replace(placeholder, str(value))
        return content

    def exists(self, name: str) -> bool:
        """Check whether a prompt file exists without loading it."""
        path = self._resolve(name)
        return os.path.exists(path)

    def clear_cache(self) -> None:
        """Clear the in-memory cache.  Useful during development."""
        self._cache.clear()

    # ── Internals ───────────────────────────────────────

    def _resolve(self, name: str) -> str:
        """Convert a dotted name to an absolute file path."""
        normalised = name.replace("/", os.sep)
        path = os.path.normpath(os.path.join(self._base_dir, f"{normalised}.md"))
        if not path.startswith(os.path.normpath(self._base_dir)):
            raise ValueError(f"Invalid prompt name: {name}")
        return path

    def _load_raw(self, name: str) -> str:
        """Read a prompt file from disk (with caching)."""
        if name in self._cache:
            return self._cache[name]

        path = self._resolve(name)
        if not os.path.exists(path):
            raise PromptNotFoundError(
                f"Prompt '{name}' not found at {path}"
            )

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self._cache[name] = content
        return content


# Global singleton — PromptLoader is stateless and globally shared.
prompt_loader = PromptLoader()
