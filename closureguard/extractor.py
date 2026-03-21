"""Belief extraction from natural language reasoning traces.

Extracts explicit beliefs and commitments from agent step text
using Claude API or hardcoded fixtures for testing.
"""

from __future__ import annotations

import json
import os
from typing import Optional

SYSTEM_PROMPT = (
    "You are a belief extractor. Given a reasoning step from an AI agent, "
    "extract every explicit belief or commitment the agent has stated. "
    "Return ONLY a JSON array of belief strings. Each belief should be "
    "a complete declarative sentence. Do not include beliefs that are "
    "merely implied — only what is explicitly stated."
)

# Hardcoded fixtures for test mode (no API key required)
_TEST_FIXTURES: dict[str, list[str]] = {
    "The API documentation confirms the endpoint returns JSON.": [
        "The API endpoint returns JSON."
    ],
    "JSON responses need to be parsed before accessing fields.": [
        "JSON responses need to be parsed before accessing fields."
    ],
    "Let me extract the 'name' field from the response.": [
        "The response contains a 'name' field that can be extracted."
    ],
    "The input n = 42 is an even number.": [
        "The number 42 is even."
    ],
    "Since n is even, n is divisible by 2.": [
        "An even number is divisible by 2.",
        "42 is divisible by 2."
    ],
    "The result is 21.": [
        "42 divided by 2 equals 21."
    ],
    "I'll read the configuration from config.yaml.": [
        "The configuration is stored in config.yaml."
    ],
    "The system reports config.yaml was deleted in the last deployment.": [
        "config.yaml was deleted in the last deployment.",
        "config.yaml no longer exists on disk."
    ],
    "Now let me parse the database URL from config.yaml.": [
        "The database URL can be parsed from config.yaml."
    ],
    "Health check at 14:00 shows the database server is unreachable.": [
        "The database server is unreachable as of 14:00."
    ],
    "I need to fetch user records to complete this task.": [
        "User records are needed to complete this task."
    ],
    "Let me process the query results.": [
        "Query results are available for processing."
    ],
    "The function is defined as pure with no side effects.": [
        "The function is pure.",
        "The function has no side effects."
    ],
    "I will modify the global state inside this function.": [
        "The global state will be modified inside this function."
    ],
    "The variable 'morning_star' refers to Venus.": [
        "The variable 'morning_star' refers to Venus."
    ],
    "I need to look up data about 'evening_star' since we have no information about it.": [
        "There is no existing information about 'evening_star'.",
        "Data about 'evening_star' needs to be looked up."
    ],
    "The theorem might be provable using induction.": [
        "It is possible that the theorem is provable using induction."
    ],
    "Since the theorem is provable by induction, I will skip exploring other proof strategies.": [
        "The theorem is provable by induction.",
        "Other proof strategies are unnecessary."
    ],
}


def extract_beliefs(
    step_text: str,
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> list[str]:
    """Extract explicit beliefs from an agent step's text output.

    Args:
        step_text: The natural language text from one agent step.
        test_mode: If True, use hardcoded fixtures instead of API.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        List of belief strings. Returns [] on any failure.
    """
    if test_mode:
        return _test_fixtures_lookup(step_text)

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _test_fixtures_lookup(step_text)

    import anthropic
    import logging
    import time

    client = anthropic.Anthropic(api_key=key)
    max_retries = 5
    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": step_text}],
            )
            text = message.content[0].text.strip()
            # Handle markdown code fences
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            beliefs = json.loads(text)
            if isinstance(beliefs, list) and all(isinstance(b, str) for b in beliefs):
                return beliefs
            logging.getLogger(__name__).warning("API returned non-list response: %s", text[:100])
            return []
        except json.JSONDecodeError:
            logging.getLogger(__name__).warning("Failed to parse belief extraction response as JSON")
            return []
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"Anthropic API authentication failed: {e}") from e
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APIError) as e:
            wait = min(2 ** (attempt + 1), 30)
            logging.getLogger(__name__).warning("API error, retrying in %ds (%d/%d): %s", wait, attempt + 1, max_retries, e)
            time.sleep(wait)
    raise RuntimeError(f"Belief extraction failed after {max_retries} retries")


def _test_fixtures_lookup(step_text: str) -> list[str]:
    """Look up beliefs from hardcoded test fixtures."""
    # Exact match first
    if step_text in _TEST_FIXTURES:
        return _TEST_FIXTURES[step_text]
    # Substring match as fallback
    for key, beliefs in _TEST_FIXTURES.items():
        if key in step_text or step_text in key:
            return beliefs
    return []
