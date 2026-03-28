"""Anthropic (Claude) provider for belief extraction."""

from __future__ import annotations

from typing import Optional

from nous.extractor import SYSTEM_PROMPT, extract_beliefs, _test_fixtures_lookup


class AnthropicProvider:
    """Extract beliefs using Claude API.

    Wraps the existing extractor.py logic with the Provider interface.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model = model

    def extract(self, text: str) -> list[str]:
        """Extract beliefs from text using Claude."""
        if not self.api_key:
            return _test_fixtures_lookup(text)
        return extract_beliefs(text, api_key=self.api_key)
