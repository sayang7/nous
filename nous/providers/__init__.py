"""LLM providers for belief extraction.

Any-LLM support: extract beliefs from reasoning text using
whichever LLM the user prefers. The core graph algorithms
don't care which provider extracts the beliefs.

Usage:
    from nous.providers import get_provider

    provider = get_provider("anthropic")  # or "openai", "ollama"
    beliefs = provider.extract("The catalyst is air-sensitive.")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from nous.providers.anthropic_provider import AnthropicProvider
from nous.providers.openai_provider import OpenAIProvider


class Provider(ABC):
    """Abstract interface for belief extraction from any LLM."""

    @abstractmethod
    def extract(self, text: str) -> list[str]:
        """Extract beliefs/commitments from natural language text.

        Args:
            text: Natural language reasoning step.

        Returns:
            List of declarative belief strings.
        """
        ...


def get_provider(
    name: str = "auto",
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Provider:
    """Get an LLM provider for belief extraction.

    Args:
        name: "anthropic", "openai", "ollama", or "auto".
        api_key: API key for the provider.
        model: Model name override.

    Returns:
        A Provider instance.
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
    elif name == "auto":
        # Try Anthropic first, then OpenAI
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return AnthropicProvider(api_key=key, model=model)

        key = os.environ.get("OPENAI_API_KEY")
        if key:
            return OpenAIProvider(api_key=key, model=model)

        raise RuntimeError(
            "No LLM provider available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )
    else:
        raise ValueError(f"Unknown provider: {name}. Use 'anthropic', 'openai', or 'auto'.")
