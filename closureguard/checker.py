"""Entailment and violation checking between belief/action pairs.

Determines whether a prior belief and a subsequent action/belief
are coherent, using Claude API or rule-based fixtures for testing.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Violation types matching the Lean taxonomy
VIOLATION_TYPES = {
    "ModusPonensViolation",
    "BeliefRevisionFailure",
    "ModalScopeError",
    "TemporalCoherenceViolation",
    "ReferentialOpacityFailure",
}

COHERENCE_CHECK_PROMPT = """\
You are an epistemic closure violation detector. Your task is to determine \
whether a specific action DIRECTLY contradicts a commitment entailed by a \
prior belief.

Prior belief: {belief_a}
Subsequent action or belief: {belief_b}

IMPORTANT: Only judge VIOLATION if the action is LOGICALLY INCOMPATIBLE with \
what the prior belief entails. Do NOT flag:
- Actions that are merely tangential, redundant, or suboptimal
- Actions that build on or extend the prior belief in a new direction
- Actions that are consistent with the belief even if they seem unrelated
- Actions where the belief was correctly updated or revised before acting

A VIOLATION requires: the prior belief commits the agent to X, and the action \
directly presupposes NOT-X without the agent ever revising the belief.

Default to COHERENT unless the violation is clear and direct.

Respond in EXACTLY this JSON format (no markdown):
{{
  "judgment": "VIOLATION" or "COHERENT",
  "violation_type": one of ["ModusPonensViolation", "BeliefRevisionFailure", \
"ModalScopeError", "TemporalCoherenceViolation", "ReferentialOpacityFailure"] \
or null if coherent,
  "confidence": float between 0.0 and 1.0,
  "explanation": "one sentence explaining the judgment"
}}"""


@dataclass
class EntailmentResult:
    """Result of a coherence check between a prior belief and action/belief."""

    entails: bool
    confidence: float  # 0.0 to 1.0
    violation_type: Optional[str] = None
    explanation: Optional[str] = None


# Cache to avoid redundant API calls
_cache: dict[tuple[str, str], EntailmentResult] = {}

# Hardcoded pairs for test mode. Each entry now includes violation_type
# and explanation for violations, matching the structured API response.
_TEST_ENTAILMENTS: dict[tuple[str, str], EntailmentResult] = {
    # ── ModusPonensViolation: API returns JSON ──
    ("The API endpoint returns JSON.",
     "The response must be parsed as JSON to extract fields."
     ): EntailmentResult(True, 0.92),
    ("JSON responses need to be parsed before accessing fields.",
     "The response must be parsed as JSON to extract fields."
     ): EntailmentResult(True, 0.95),
    ("The API endpoint returns JSON.",
     "Split response string by commas to find name."
     ): EntailmentResult(False, 0.95, "ModusPonensViolation",
        "Treating JSON response as plain text contradicts the commitment to parse as JSON."),
    ("JSON responses need to be parsed before accessing fields.",
     "Split response string by commas to find name."
     ): EntailmentResult(False, 0.93, "ModusPonensViolation",
        "String-splitting contradicts the stated requirement to parse JSON."),

    # ── BeliefRevisionFailure: file deleted ──
    ("config.yaml was deleted in the last deployment.",
     "config.yaml cannot be read because it no longer exists."
     ): EntailmentResult(True, 0.97),
    ("config.yaml no longer exists on disk.",
     "The database URL can be parsed from config.yaml."
     ): EntailmentResult(False, 0.94, "BeliefRevisionFailure",
        "Cannot parse from a file that the agent knows was deleted."),
    ("config.yaml was deleted in the last deployment.",
     "The database URL can be parsed from config.yaml."
     ): EntailmentResult(False, 0.96, "BeliefRevisionFailure",
        "Agent failed to revise its plan after learning the file was deleted."),
    ("config.yaml was deleted in the last deployment.",
     "Read database_url field from config.yaml."
     ): EntailmentResult(False, 0.96, "BeliefRevisionFailure",
        "Reading from a deleted file contradicts the agent's own knowledge."),
    ("config.yaml no longer exists on disk.",
     "Read database_url field from config.yaml."
     ): EntailmentResult(False, 0.94, "BeliefRevisionFailure",
        "Cannot read from a file the agent knows no longer exists."),

    # ── TemporalCoherenceViolation: server unreachable ──
    ("The database server is unreachable as of 14:00.",
     "Queries to the database server will fail."
     ): EntailmentResult(True, 0.94),
    ("The database server is unreachable as of 14:00.",
     "Query results are available for processing."
     ): EntailmentResult(False, 0.95, "TemporalCoherenceViolation",
        "Cannot have query results from an unreachable server."),
    ("The database server is unreachable as of 14:00.",
     "Query the database server for user records."
     ): EntailmentResult(False, 0.94, "TemporalCoherenceViolation",
        "Querying a server known to be unreachable contradicts the agent's knowledge."),

    # ── Coherent: even number reasoning ──
    ("The number 42 is even.",
     "42 is divisible by 2."): EntailmentResult(True, 0.99),
    ("An even number is divisible by 2.",
     "42 divided by 2 equals 21."): EntailmentResult(True, 0.88),

    # ── ModalScopeError: possible vs necessary ──
    ("It is possible that the theorem is provable using induction.",
     "The theorem is provable by induction."
     ): EntailmentResult(False, 0.88, "ModalScopeError",
        "Possibility was treated as certainty without additional evidence."),
    ("It is possible that the theorem is provable using induction.",
     "Begin induction proof directly."
     ): EntailmentResult(False, 0.85, "ModalScopeError",
        "Committing to induction without confirming it works confuses possibility with necessity."),
    ("It is possible that the theorem is provable using induction.",
     "Other proof strategies are unnecessary."
     ): EntailmentResult(False, 0.90, "ModalScopeError",
        "Dismissing alternatives based on mere possibility is a modal scope error."),

    # ── ReferentialOpacityFailure ──
    ("The variable 'morning_star' refers to Venus.",
     "There is no existing information about 'evening_star'."
     ): EntailmentResult(False, 0.82, "ReferentialOpacityFailure",
        "If morning_star refers to Venus and evening_star also refers to Venus, existing info should transfer."),

    # ── Pure function violations ──
    ("The function is pure.",
     "The function has no side effects."): EntailmentResult(True, 0.96),
    ("The function has no side effects.",
     "The global state will be modified inside this function."
     ): EntailmentResult(False, 0.97, "ModusPonensViolation",
        "Modifying global state contradicts the commitment that the function has no side effects."),
    ("The function is pure.",
     "Write global_counter += 1 in the function body."
     ): EntailmentResult(False, 0.96, "ModusPonensViolation",
        "Writing to a global counter contradicts the commitment to purity."),
    ("The function has no side effects.",
     "Write global_counter += 1 in the function body."
     ): EntailmentResult(False, 0.97, "ModusPonensViolation",
        "Writing to a global counter is a side effect, contradicting the stated belief."),
}


def check_entailment(
    belief_a: str,
    belief_b: str,
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> EntailmentResult:
    """Check whether a prior belief and subsequent action/belief are coherent.

    Args:
        belief_a: The prior belief/commitment.
        belief_b: The subsequent belief or action description.
        test_mode: If True, use hardcoded rules instead of API.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        EntailmentResult with coherence judgment and violation details.
    """
    cache_key = (belief_a, belief_b)
    if cache_key in _cache:
        return _cache[cache_key]

    if test_mode:
        result = _test_entailment_lookup(belief_a, belief_b)
    else:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            result = _test_entailment_lookup(belief_a, belief_b)
        else:
            result = _api_coherence_check(belief_a, belief_b, key)

    _cache[cache_key] = result
    return result


def clear_cache() -> None:
    """Clear the entailment cache."""
    _cache.clear()


def _api_coherence_check(
    belief_a: str, belief_b: str, api_key: str, max_retries: int = 5
) -> EntailmentResult:
    """Check belief-action coherence using Claude API with structured output."""
    import anthropic
    import time

    client = anthropic.Anthropic(api_key=api_key)
    prompt = COHERENCE_CHECK_PROMPT.format(belief_a=belief_a, belief_b=belief_b)

    last_error = None
    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text.strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            parsed = json.loads(text)
            judgment = parsed.get("judgment", "COHERENT").upper()
            is_coherent = judgment == "COHERENT"
            violation_type = parsed.get("violation_type")
            confidence = float(parsed.get("confidence", 0.5))
            explanation = parsed.get("explanation")

            # Validate violation type
            if violation_type and violation_type not in VIOLATION_TYPES:
                violation_type = "ModusPonensViolation"  # safe default

            return EntailmentResult(
                entails=is_coherent,
                confidence=confidence,
                violation_type=violation_type if not is_coherent else None,
                explanation=explanation,
            )

        except json.JSONDecodeError:
            logger.warning("Failed to parse coherence check response as JSON, using fallback")
            return _test_entailment_lookup(belief_a, belief_b)
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"Anthropic API authentication failed: {e}") from e
        except anthropic.RateLimitError:
            wait = min(2 ** (attempt + 1), 30)
            logger.warning("Rate limited, retrying in %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
            time.sleep(wait)
            last_error = "rate_limit"
        except (anthropic.APIConnectionError, anthropic.APIError) as e:
            wait = min(2 ** (attempt + 1), 30)
            logger.warning("API error, retrying in %ds (attempt %d/%d): %s", wait, attempt + 1, max_retries, e)
            time.sleep(wait)
            last_error = e

    raise RuntimeError(f"Anthropic API failed after {max_retries} retries: {last_error}")


def _test_entailment_lookup(belief_a: str, belief_b: str) -> EntailmentResult:
    """Look up entailment from hardcoded test pairs."""
    key = (belief_a, belief_b)
    if key in _TEST_ENTAILMENTS:
        return _TEST_ENTAILMENTS[key]
    # Default: coherent (no violation detected in test mode for unknown pairs)
    return EntailmentResult(entails=True, confidence=0.5, explanation="No matching fixture")
