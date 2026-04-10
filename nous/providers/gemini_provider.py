"""Google Gemini provider for belief extraction and reasoning."""

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


class GeminiProvider:
    """Extract beliefs and generate reasoning using Google Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model = model or "gemini-1.5-flash"

    def _get_client(self):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "GeminiProvider requires google-generativeai. "
                "Install with: pip install google-generativeai"
            )
        genai.configure(api_key=self.api_key)
        return genai

    def extract(self, text: str) -> list[str]:
        """Extract beliefs from text using Gemini."""
        if not self.api_key:
            return _test_fixtures_lookup(text)

        genai = self._get_client()

        try:
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=SYSTEM_PROMPT,
            )
            response = model.generate_content(
                text,
                generation_config={"temperature": 0.0, "max_output_tokens": 1024},
            )
            content = response.text.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            beliefs = json.loads(content)
            if isinstance(beliefs, list) and all(isinstance(b, str) for b in beliefs):
                return beliefs
            logger.warning("Gemini extract() returned non-list: %s", content[:100])
            return []
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini extract() response as JSON")
            return []
        except Exception as e:
            logger.warning("Gemini extraction failed: %s", e)
            return []

    def reason(self, problem: str) -> list[dict]:
        """Send a problem to Gemini and return structured reasoning steps.

        Args:
            problem: The question or problem to reason about.

        Returns:
            List of {text, action} dicts representing reasoning steps.
        """
        if not self.api_key:
            raise RuntimeError("API key required for reason(). Set GEMINI_API_KEY.")

        genai = self._get_client()

        try:
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=REASON_PROMPT,
            )
            response = model.generate_content(
                problem,
                generation_config={"temperature": 0.7, "max_output_tokens": 2048},
            )
            content = response.text.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            steps = json.loads(content)
            if isinstance(steps, list):
                return [
                    {"text": str(s.get("text", "")), "action": str(s.get("action", ""))}
                    for s in steps
                    if isinstance(s, dict)
                ]
            logger.warning("Gemini reason() returned non-list: %s", content[:100])
            return []
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini reason() response as JSON")
            return []
        except Exception as e:
            logger.warning("Gemini reason() failed: %s", e)
            raise
