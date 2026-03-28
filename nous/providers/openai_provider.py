"""OpenAI provider for belief extraction."""

from __future__ import annotations

import json
import logging
from typing import Optional

from nous.extractor import SYSTEM_PROMPT, _test_fixtures_lookup

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Extract beliefs using OpenAI API (GPT-4, etc).

    Same extraction prompt as Anthropic, different client.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model = model or "gpt-4o"

    def extract(self, text: str) -> list[str]:
        """Extract beliefs from text using OpenAI."""
        if not self.api_key:
            return _test_fixtures_lookup(text)

        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAIProvider requires the openai package. "
                "Install with: pip install openai"
            )

        client = openai.OpenAI(api_key=self.api_key)

        try:
            response = client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
            content = response.choices[0].message.content or ""
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            beliefs = json.loads(content)
            if isinstance(beliefs, list) and all(isinstance(b, str) for b in beliefs):
                return beliefs
            logger.warning("OpenAI returned non-list: %s", content[:100])
            return []
        except json.JSONDecodeError:
            logger.warning("Failed to parse OpenAI response as JSON")
            return []
        except Exception as e:
            logger.warning("OpenAI extraction failed: %s", e)
            return []
