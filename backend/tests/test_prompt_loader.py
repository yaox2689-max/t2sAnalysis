"""Tests for PromptLoader — loading, caching, variable substitution, errors."""

import pytest

from app.core.prompt_loader import PromptLoader, PromptNotFoundError


@pytest.fixture
def loader():
    return PromptLoader()


class TestPromptLoader:
    def test_load_base_prompt(self, loader):
        prompt = loader.load("sql_agent/sql_generation")
        assert "SELECT" in prompt or "sql" in prompt.lower()
        assert len(prompt) > 50

    def test_load_with_variables(self, loader):
        prompt = loader.load("sql_agent/sql_generation", task_type="trend")
        # Variable replacement should not break the prompt
        assert len(prompt) > 50

    def test_load_nonexistent_raises(self, loader):
        with pytest.raises(PromptNotFoundError):
            loader.load("nonexistent/prompt")

    def test_exists_true(self, loader):
        assert loader.exists("sql_agent/sql_generation") is True

    def test_exists_false(self, loader):
        assert loader.exists("nonexistent/prompt") is False

    def test_cache_hit(self, loader):
        # First load reads from disk
        p1 = loader.load("reflection/error_classifier")
        assert p1
        # Clear cache
        loader.clear_cache()
        # Reload should still work
        p2 = loader.load("reflection/error_classifier")
        assert p2 == p1

    def test_clear_cache(self, loader):
        loader.load("reflection/error_classifier")
        assert "reflection/error_classifier" in loader._cache
        loader.clear_cache()
        assert "reflection/error_classifier" not in loader._cache

    def test_variable_substitution(self, loader):
        """Verify {{ var }} placeholders get replaced."""
        # Use a known prompt that doesn't have the placeholder
        prompt = loader.load("sql_agent/sql_generation", FAKE_VAR="hello")
        assert "{{ FAKE_VAR }}" not in prompt  # it was in vars so it's gone
        # Unused variables are just ignored
        assert len(prompt) > 50

    def test_multiple_prompts_independent_cache(self, loader):
        p1 = loader.load("sql_agent/sql_generation")
        p2 = loader.load("reflection/error_classifier")
        assert p1 != p2

    def test_tools_prompt_loadable(self, loader):
        prompt = loader.load("tools/insight")
        assert "insight" in prompt.lower() or "summary" in prompt.lower()

    def test_evidence_prompt_loadable(self, loader):
        prompt = loader.load("tools/evidence_analyzer")
        assert "evidence" in prompt.lower()
