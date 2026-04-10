"""LLM providers for belief extraction and reasoning generation.

Any-LLM support: extract beliefs from reasoning text and generate reasoning
using whichever LLM the user prefers. The core graph algorithms are provider-agnostic.

Usage:
    from nous.providers import get_provider

    # Belief extraction
    provider = get_provider("anthropic")
    beliefs = provider.extract("The catalyst is air-sensitive.")

    # Reasoning generation
    provider = get_provider("openai", api_key="sk-...")
    steps = provider.reason("Is it safe to open the flask to air?")
    # → [{"text": "...", "action": "..."}, ...]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from nous.providers.anthropic_provider import AnthropicProvider
from nous.providers.openai_provider import OpenAIProvider
from nous.providers.gemini_provider import GeminiProvider


class Provider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def extract(self, text: str) -> list[str]:
        """Extract beliefs/commitments from natural language text.

        Args:
            text: Natural language reasoning step.

        Returns:
            List of declarative belief strings.
        """
        ...

    @abstractmethod
    def reason(self, problem: str) -> list[dict]:
        """Generate step-by-step reasoning for a problem.

        Args:
            problem: A question or problem statement.

        Returns:
            List of {text, action} dicts representing reasoning steps.
        """
        ...


def get_provider(
    name: str = "auto",
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> AnthropicProvider | OpenAIProvider | GeminiProvider:
    """Get an LLM provider.

    Args:
        name: "anthropic", "openai", "gemini", or "auto".
        api_key: API key for the provider (overrides env vars).
        model: Model name override.

    Returns:
        A provider instance with extract() and reason() methods.
    """
    import os

    if name == "anthropic":
        return AnthropicProvider(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            model=model,
        )
    elif name == "openai":
        return OpenAIProvider(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            model=model,
        )
    elif name == "gemini":
        return GeminiProvider(
            api_key=api_key or os.environ.get("GEMINI_API_KEY"),
            model=model,
        )
    elif name == "auto":
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return AnthropicProvider(api_key=key, model=model)

        key = os.environ.get("OPENAI_API_KEY")
        if key:
            return OpenAIProvider(api_key=key, model=model)

        key = os.environ.get("GEMINI_API_KEY")
        if key:
            return GeminiProvider(api_key=key, model=model)

        raise RuntimeError(
            "No LLM provider available. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY."
        )
    else:
        raise ValueError(
            f"Unknown provider: {name!r}. Use 'anthropic', 'openai', 'gemini', or 'auto'."
        )
