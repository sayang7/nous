"""OpenAI provider for belief extraction and reasoning."""

from __future__ import annotations

import json
import logging
from typing import Optional

from nous.extractor import SYSTEM_PROMPT, _test_fixtures_lookup

logger = logging.getLogger(__name__)

REASON_PROMPT = """\
You are a philosophical reasoning engine. When given a question, reason through it with genuine depth — \
surface hidden assumptions, follow implications to their logical ends, explore what must be true for each \
claim to hold, and commit fully to your conclusions even when they create tension with earlier steps. \
Don't hedge. Don't summarise. Think.

Return ONLY a JSON array — no other text, no markdown fences:
[
  {"text": "Your reasoning at this step: the observation, assumption, or implication you are exploring", \
"action": "The definite claim or commitment you are making — what must now be true given this step"},
  ...
]

Rules:
- 5–9 steps
- Each step should surface something non-obvious: a hidden premise, a logical consequence, a \
metaphysical assumption, a historical pattern, a structural constraint
- Make strong, specific commitments in "action" — not "we should consider X" but "X entails Y", \
"therefore Z is impossible", "we must assume A for this to hold"
- Later steps may and should build on, extend, or collide with earlier ones — \
that tension is the point
- Reason across levels freely: logical, mathematical, philosophical, historical, structural
- Ask what the question reveals about the nature of the domain, not just what the answer is
"""


class OpenAIProvider:
    """Extract beliefs and generate reasoning using OpenAI API (GPT-4, etc)."""

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

    def reason(self, problem: str) -> list[dict]:
        """Send a problem to GPT and return structured reasoning steps.

        Args:
            problem: The question or problem to reason about.

        Returns:
            List of {text, action} dicts representing reasoning steps.
        """
        if not self.api_key:
            raise RuntimeError("API key required for reason(). Set OPENAI_API_KEY.")

        try:
            import openai
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

        client = openai.OpenAI(api_key=self.api_key)

        try:
            response = client.chat.completions.create(
                model=self.model,
                temperature=0.7,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": REASON_PROMPT},
                    {"role": "user", "content": problem},
                ],
            )
            content = response.choices[0].message.content or ""
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            steps = json.loads(content)
            if isinstance(steps, list):
                return [
                    {"text": str(s.get("text", "")), "action": str(s.get("action", ""))}
                    for s in steps
                    if isinstance(s, dict)
                ]
            logger.warning("OpenAI reason() returned non-list: %s", content[:100])
            return []
        except json.JSONDecodeError:
            logger.warning("Failed to parse OpenAI reason() response as JSON")
            return []
        except Exception as e:
            logger.warning("OpenAI reason() failed: %s", e)
            raise
