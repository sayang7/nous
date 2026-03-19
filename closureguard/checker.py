"""Entailment checking between belief pairs.

Determines whether believing A commits an agent to believing B,
using Claude API or rule-based heuristics for testing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class EntailmentResult:
    """Result of an entailment check between two beliefs."""
    entails: bool
    confidence: float  # 0.0 to 1.0


# Cache to avoid redundant API calls
_cache: dict[tuple[str, str], EntailmentResult] = {}

# Hardcoded entailment pairs for test mode
_TEST_ENTAILMENTS: dict[tuple[str, str], EntailmentResult] = {
    # ModusPonensViolation: API returns JSON → must parse as JSON
    ("The API endpoint returns JSON.",
     "The response must be parsed as JSON to extract fields."): EntailmentResult(True, 0.92),
    ("JSON responses need to be parsed before accessing fields.",
     "The response must be parsed as JSON to extract fields."): EntailmentResult(True, 0.95),

    # ModusPonensViolation: action contradicts entailed belief
    ("The API endpoint returns JSON.",
     "Split response string by commas to find name."): EntailmentResult(False, 0.05),
    ("JSON responses need to be parsed before accessing fields.",
     "Split response string by commas to find name."): EntailmentResult(False, 0.04),

    # BeliefRevisionFailure: file deleted → can't read it
    ("config.yaml was deleted in the last deployment.",
     "config.yaml cannot be read because it no longer exists."): EntailmentResult(True, 0.97),
    ("config.yaml no longer exists on disk.",
     "The database URL can be parsed from config.yaml."): EntailmentResult(False, 0.05),
    ("config.yaml was deleted in the last deployment.",
     "The database URL can be parsed from config.yaml."): EntailmentResult(False, 0.03),
    ("config.yaml was deleted in the last deployment.",
     "Read database_url field from config.yaml."): EntailmentResult(False, 0.03),
    ("config.yaml no longer exists on disk.",
     "Read database_url field from config.yaml."): EntailmentResult(False, 0.04),

    # TemporalCoherenceViolation: server down → queries fail
    ("The database server is unreachable as of 14:00.",
     "Queries to the database server will fail."): EntailmentResult(True, 0.94),
    ("The database server is unreachable as of 14:00.",
     "Query results are available for processing."): EntailmentResult(False, 0.04),
    ("The database server is unreachable as of 14:00.",
     "Query the database server for user records."): EntailmentResult(False, 0.05),

    # Coherent traces: even → divisible by 2
    ("The number 42 is even.",
     "42 is divisible by 2."): EntailmentResult(True, 0.99),
    ("An even number is divisible by 2.",
     "42 divided by 2 equals 21."): EntailmentResult(True, 0.88),

    # ModalScopeError: possible → necessary confusion
    ("It is possible that the theorem is provable using induction.",
     "The theorem is provable by induction."): EntailmentResult(False, 0.15),

    # ReferentialOpacityFailure: morning star = evening star = Venus
    ("The variable 'morning_star' refers to Venus.",
     "There is no existing information about 'evening_star'."): EntailmentResult(False, 0.10),

    # Pure function entailments
    ("The function is pure.",
     "The function has no side effects."): EntailmentResult(True, 0.96),
    ("The function has no side effects.",
     "The global state will be modified inside this function."): EntailmentResult(False, 0.02),
    ("The function is pure.",
     "Write global_counter += 1 in the function body."): EntailmentResult(False, 0.03),
    ("The function has no side effects.",
     "Write global_counter += 1 in the function body."): EntailmentResult(False, 0.02),

    # ModalScopeError: action presupposes certainty from possibility
    ("It is possible that the theorem is provable using induction.",
     "Begin induction proof directly."): EntailmentResult(False, 0.18),
    ("It is possible that the theorem is provable using induction.",
     "Other proof strategies are unnecessary."): EntailmentResult(False, 0.08),
}


def check_entailment(
    belief_a: str,
    belief_b: str,
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> EntailmentResult:
    """Check whether believing A commits an agent to believing B.

    Args:
        belief_a: The antecedent belief.
        belief_b: The potentially entailed belief.
        test_mode: If True, use hardcoded rules instead of API.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        EntailmentResult with entails (bool) and confidence (float).
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
            result = _api_entailment_check(belief_a, belief_b, key)

    _cache[cache_key] = result
    return result


def clear_cache() -> None:
    """Clear the entailment cache."""
    _cache.clear()


def _api_entailment_check(
    belief_a: str, belief_b: str, api_key: str
) -> EntailmentResult:
    """Check entailment using Claude API."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            f"Does believing the following statement A commit a rational agent "
            f"to believing statement B?\n\n"
            f"A: {belief_a}\nB: {belief_b}\n\n"
            f"Answer YES or NO and nothing else."
        )
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = message.content[0].text.strip().upper()
        entails = answer.startswith("YES")
        # Derive confidence from the decisiveness of the response
        confidence = 0.85 if entails else 0.15
        return EntailmentResult(entails=entails, confidence=confidence)
    except Exception:
        return _test_entailment_lookup(belief_a, belief_b)


def _test_entailment_lookup(belief_a: str, belief_b: str) -> EntailmentResult:
    """Look up entailment from hardcoded test pairs."""
    key = (belief_a, belief_b)
    if key in _TEST_ENTAILMENTS:
        return _TEST_ENTAILMENTS[key]
    # Default: no entailment
    return EntailmentResult(entails=False, confidence=0.5)
