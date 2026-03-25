"""Belief extraction from natural language reasoning traces.

Extracts explicit beliefs and commitments from agent step text
using Claude API or hardcoded fixtures for testing.
"""

from __future__ import annotations

import json
import os
from typing import Optional

# Default model for API calls. Can be overridden via CLOSUREGUARD_MODEL env var.
DEFAULT_MODEL = "claude-sonnet-4-6"

def _get_model() -> str:
    return os.environ.get("CLOSUREGUARD_MODEL", DEFAULT_MODEL)

SYSTEM_PROMPT = (
    "You are a belief and commitment extractor for epistemic closure analysis. "
    "Given a reasoning step from an AI agent, extract:\n"
    "1. Every EXPLICIT belief the agent states (what it directly asserts).\n"
    "2. Every INFERENTIAL COMMITMENT the agent incurs by making those assertions "
    "(what logically follows from the explicit beliefs, even if unsaid). "
    "This is key: when an agent asserts P, and P logically entails Q, the agent "
    "is committed to Q — even if it never says Q explicitly.\n\n"
    "Examples of inferential commitments:\n"
    "- 'The file is read-only' → committed to 'Writing to the file will fail'\n"
    "- 'The server is down' → committed to 'Requests to the server will fail'\n"
    "- 'The catalyst is air-sensitive' → committed to 'Exposing catalyst to air will damage it'\n"
    "- 'X inhibits Y' + 'Y activates Z' → committed to 'X impairs Z'\n\n"
    "Return ONLY a JSON array of belief/commitment strings. Each should be "
    "a complete declarative sentence. Include both explicit beliefs AND their "
    "immediate inferential commitments (one step of logical consequence)."
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
    # ── Demo 1: Theorem Proving (assumption drift) ──
    "Function f is continuous on the closed interval [a,b]. This follows from the composition of continuous functions.": [
        "Function f is continuous on [a,b].",
    ],
    "By the Intermediate Value Theorem, since f is continuous on [a,b] and f(a) < 0 < f(b), there exists c in (a,b) with f(c) = 0.": [
        "f is continuous on [a,b].",
        "The Intermediate Value Theorem applies to f on [a,b].",
        "There exists c in (a,b) with f(c) = 0.",
    ],
    "To find extrema, I need to find critical points. Since f is differentiable everywhere on (a,b), I can compute f'(x) and set it to zero.": [
        "f is differentiable everywhere on (a,b).",
        "Critical points can be found by setting f'(x) = 0.",
    ],
    # ── Demo 2: Experimental Protocol (safety violation) ──
    "The palladium catalyst is air-sensitive and must be handled under inert atmosphere (N2 or Ar). Exposure to oxygen will deactivate it.": [
        "The palladium catalyst is air-sensitive.",
        "The catalyst must be handled under inert atmosphere.",
        "Exposure to oxygen will deactivate the catalyst.",
    ],
    "Weigh 50mg of catalyst in the glovebox and transfer to the Schlenk flask under nitrogen.": [
        "The catalyst is transferred under nitrogen atmosphere.",
    ],
    "Add the substrate and solvent. To ensure complete mixing, briefly open the flask to air to add the reagent via syringe.": [
        "The flask is opened to air.",
        "The reagent is added via syringe.",
    ],
    # ── Demo 3: Literature Synthesis (contradictory recommendation) ──
    "Paper A (Chen et al. 2024) reports that compound X is a potent inhibitor of kinase Y, with IC50 = 12nM.": [
        "Compound X inhibits kinase Y.",
    ],
    "Paper B (Zhang et al. 2025) shows that kinase Y is essential for activating pathway Z. Knockout of kinase Y abolishes pathway Z activity entirely.": [
        "Kinase Y is essential for activating pathway Z.",
        "Without kinase Y, pathway Z is abolished.",
    ],
    "Synthesizing these findings: since X inhibits Y, and Y is required for Z, compound X would impair pathway Z signaling.": [
        "Compound X impairs pathway Z signaling.",
        "X inhibits Y and Y is required for Z.",
    ],
    "Based on the literature, we recommend compound X as a potential enhancer of pathway Z for therapeutic applications.": [
        "Compound X is recommended as an enhancer of pathway Z.",
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
    max_retries = 3
    for attempt in range(max_retries):
        try:
            text_parts = []
            with client.messages.stream(
                model=_get_model(),
                max_tokens=1024,
                temperature=0.0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": step_text}],
            ) as stream:
                for chunk in stream.text_stream:
                    text_parts.append(chunk)
            text = "".join(text_parts).strip()
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


BATCH_SYSTEM_PROMPT = (
    "You are a belief and commitment extractor for epistemic closure analysis. "
    "Given multiple numbered reasoning steps from an AI agent, extract from EACH step:\n"
    "1. Every EXPLICIT belief the agent states.\n"
    "2. Every INFERENTIAL COMMITMENT incurred by those assertions "
    "(what logically follows, even if unsaid). When an agent asserts P and P entails Q, "
    "the agent is committed to Q.\n\n"
    "Return ONLY a JSON object mapping step indices to arrays of belief/commitment strings. "
    "Each should be a complete declarative sentence. Include both explicit beliefs AND "
    "immediate inferential commitments (one step of logical consequence)."
)


def extract_beliefs_batch(
    steps: list[str],
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> list[list[str]]:
    """Extract beliefs from multiple steps in a single API call.

    Args:
        steps: List of step text strings.
        test_mode: If True, use hardcoded fixtures.
        api_key: Anthropic API key.

    Returns:
        List of belief lists, one per step, in order.
    """
    if not steps:
        return []

    if test_mode:
        return [_test_fixtures_lookup(s) for s in steps]

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return [_test_fixtures_lookup(s) for s in steps]

    import anthropic
    import logging
    import time

    client = anthropic.Anthropic(api_key=key)

    # Build numbered steps
    lines = []
    for i, text in enumerate(steps):
        lines.append(f"[{i}] {text}")
    user_content = "\n".join(lines)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            text_parts = []
            with client.messages.stream(
                model=_get_model(),
                max_tokens=1024 * max(1, len(steps) // 3),
                temperature=0.0,
                system=BATCH_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                for chunk in stream.text_stream:
                    text_parts.append(chunk)
            text = "".join(text_parts).strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            parsed = json.loads(text)
            if isinstance(parsed, dict):
                results: list[list[str]] = []
                for i in range(len(steps)):
                    beliefs = parsed.get(str(i), parsed.get(i, []))
                    if isinstance(beliefs, list) and all(isinstance(b, str) for b in beliefs):
                        results.append(beliefs)
                    else:
                        results.append([])
                return results

            # Unexpected format, fall back to single calls
            logging.getLogger(__name__).warning("Batch response not a dict, falling back")
            return [extract_beliefs(s, api_key=key) for s in steps]

        except json.JSONDecodeError:
            logging.getLogger(__name__).warning("Failed to parse batch belief response")
            return [extract_beliefs(s, api_key=key) for s in steps]
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"Anthropic API authentication failed: {e}") from e
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APIError) as e:
            wait = min(2 ** (attempt + 1), 30)
            logging.getLogger(__name__).warning("API error, retrying in %ds (%d/%d): %s", wait, attempt + 1, max_retries, e)
            time.sleep(wait)

    raise RuntimeError(f"Batch belief extraction failed after {max_retries} retries")


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
