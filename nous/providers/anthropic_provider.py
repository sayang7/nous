"""Anthropic (Claude) provider for belief extraction and reasoning."""

from __future__ import annotations

import json
import logging
from typing import Optional

from nous.extractor import SYSTEM_PROMPT, extract_beliefs, _test_fixtures_lookup

logger = logging.getLogger(__name__)

REASON_PROMPT = """\
You are reasoning like a philosopher. At every step, you hold yourself accountable to the logical \
consequences of what you just said. You name your assumptions. You follow implications to where they \
must go. If a later step forces you to abandon an earlier commitment, say so explicitly — that is the \
mark of honest reasoning, not a failure.

When given a question, reason through it with genuine depth. Surface hidden assumptions, follow \
implications to their logical ends, explore what must be true for each claim to hold, and commit \
fully to your conclusions even when they create tension with earlier steps. Don't hedge. Don't \
summarise. Think.

Return ONLY a JSON array — no other text, no markdown fences:
[
  {
    "text": "Your reasoning at this step — the observation, assumption, or implication you are exploring",
    "action": "The definite claim you are making — what must now be true given this step",
    "assumes": ["hidden premise this step silently requires", "another if any"],
    "commits_to": ["downstream claim this step now entails", "another if any"]
  }
]

Rules:
- 5–9 steps
- "assumes": every hidden premise this step requires — what must already be true for this step to be valid. Surface the invisible imports.
- "commits_to": every downstream claim this step entails — what you are now bound to. If any later step contradicts these, that is a closure violation.
- Each step should surface something non-obvious: a hidden premise, a logical consequence, a metaphysical assumption, a historical pattern, a structural constraint
- Make strong, specific commitments in "action" — not "we should consider X" but "X entails Y", "therefore Z is impossible", "we must assume A for this to hold"
- Later steps may and should build on, extend, or collide with earlier ones — that tension is the point
- Reason across levels freely: logical, mathematical, philosophical, historical, structural
- Ask what the question reveals about the nature of the domain, not just what the answer is
"""


class AnthropicProvider:
    """Extract beliefs and generate reasoning using Claude API."""

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

    def reason(self, problem: str) -> list[dict]:
        """Send a problem to Claude and return structured reasoning steps.

        Args:
            problem: The question or problem to reason about.

        Returns:
            List of {text, action} dicts representing reasoning steps.
        """
        if not self.api_key:
            raise RuntimeError("API key required for reason(). Set ANTHROPIC_API_KEY.")

        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

        import os
        model = self.model or os.environ.get("NOUS_MODEL", "claude-sonnet-4-6")
        client = anthropic.Anthropic(api_key=self.api_key)

        try:
            message = client.messages.create(
                model=model,
                max_tokens=2048,
                temperature=0.7,
                system=REASON_PROMPT,
                messages=[{"role": "user", "content": problem}],
            )
            content = message.content[0].text.strip()
            # Strip markdown fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            steps = json.loads(content)
            if isinstance(steps, list):
                return [
                    {
                        "text": str(s.get("text", "")),
                        "action": str(s.get("action", "")),
                        "assumes": [str(a) for a in s.get("assumes", []) if isinstance(a, str)],
                        "commits_to": [str(c) for c in s.get("commits_to", []) if isinstance(c, str)],
                    }
                    for s in steps
                    if isinstance(s, dict)
                ]
            logger.warning("Claude reason() returned non-list: %s", content[:100])
            return []
        except json.JSONDecodeError:
            logger.warning("Failed to parse Claude reason() response as JSON")
            return []
        except Exception as e:
            logger.warning("Claude reason() failed: %s", e)
            raise
