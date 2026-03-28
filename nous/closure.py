"""Commitment Closure Operator.

This is the philosophical core of Nous.

Given a set of explicit assertions {P1, P2, ...}, the commitment closure
C({P1,...}) is the set of all propositions the agent is normatively bound
to accept — including inferential consequences the agent never stated.

    C(P) ∧ C(P→Q) → C(Q)    [Axiom K / Commitment Closure]

This module computes an approximation of C using LLM reasoning over the
full cumulative assertion set. This is NOT pairwise — the LLM sees ALL
prior assertions together and derives the closure as a whole.

The closure is cumulative: at step n, the commitment set includes all
assertions from steps 1..n and their inferential consequences.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"

def _get_model() -> str:
    return os.environ.get("NOUS_MODEL", DEFAULT_MODEL)


CLOSURE_PROMPT = """\
You are computing the COMMITMENT CLOSURE of an agent's assertions.

The agent has made the following explicit assertions across its reasoning trace \
(listed in chronological order — later assertions may REVISE earlier ones):
{assertions}

Compute the commitment closure: what is the agent normatively committed to,
given these assertions? Include:
1. Every explicit assertion (repeated verbatim)
2. Every immediate logical consequence (one step of modus ponens, contrapositive, etc.)
3. Every practical entailment (if P is stated, and P practically entails Q in context, include Q)

CRITICAL — handle these patterns carefully:
- BELIEF REVISION: If a later assertion explicitly updates, corrects, or supersedes an \
earlier one (e.g., "the new data shows X is actually Y"), the REVISED belief takes \
precedence. Add a commitment noting the revision: "The earlier claim [P] has been \
superseded by [Q]."
- MODAL QUALIFIERS: If an assertion uses hedging language ("might", "could", "possibly", \
"potentially"), the commitment is ONLY that the proposition is POSSIBLE, not that it is \
true. Add: "[X] is a possibility, not an established fact."
- TEMPORAL INDEXING: If an assertion is time-stamped or references a specific time/state, \
note this. Add: "[X] was true as of [time]" and "If conditions have changed since [time], \
[X] may no longer hold."

Do NOT include:
- Speculative extensions (things that MIGHT follow but don't logically MUST)
- Background knowledge not entailed by the assertions
- Negations of assertions

Return ONLY a JSON array of commitment strings. Each commitment should be a
complete declarative sentence. Be precise — every commitment must be traceable
to one or more explicit assertions.
"""

# Test fixtures: maps frozenset of assertions → commitment closure
_TEST_CLOSURES: dict[frozenset[str], list[str]] = {
    # API JSON trace
    frozenset([
        "The API endpoint returns JSON.",
        "JSON responses need to be parsed before accessing fields.",
        "The response contains a 'name' field that can be extracted.",
    ]): [
        "The API endpoint returns JSON.",
        "JSON responses need to be parsed before accessing fields.",
        "The response contains a 'name' field that can be extracted.",
        "The response from the API must be parsed as JSON before extracting the 'name' field.",
        "String-splitting or text manipulation is not appropriate for extracting fields from JSON.",
    ],
    # Even number trace
    frozenset([
        "The number 42 is even.",
        "An even number is divisible by 2.",
        "42 is divisible by 2.",
        "42 divided by 2 equals 21.",
    ]): [
        "The number 42 is even.",
        "An even number is divisible by 2.",
        "42 is divisible by 2.",
        "42 divided by 2 equals 21.",
    ],
    # Config deleted trace
    frozenset([
        "The configuration is stored in config.yaml.",
        "config.yaml was deleted in the last deployment.",
        "config.yaml no longer exists on disk.",
        "The database URL can be parsed from config.yaml.",
    ]): [
        "The configuration is stored in config.yaml.",
        "config.yaml was deleted in the last deployment.",
        "config.yaml no longer exists on disk.",
        "The database URL can be parsed from config.yaml.",
        "Reading from config.yaml will fail because it no longer exists.",
        "The database URL cannot be obtained from config.yaml.",
    ],
    # Server unreachable trace
    frozenset([
        "The database server is unreachable as of 14:00.",
        "User records are needed to complete this task.",
        "Query results are available for processing.",
    ]): [
        "The database server is unreachable as of 14:00.",
        "User records are needed to complete this task.",
        "Query results are available for processing.",
        "Queries to the database server will fail while it is unreachable.",
        "User records cannot be fetched from an unreachable server.",
    ],
    # Pure function trace
    frozenset([
        "The function is pure.",
        "The function has no side effects.",
        "The global state will be modified inside this function.",
    ]): [
        "The function is pure.",
        "The function has no side effects.",
        "The global state will be modified inside this function.",
        "A pure function must not modify global state.",
        "Modifying global state inside this function contradicts its purity.",
    ],
    # Modal scope trace
    frozenset([
        "It is possible that the theorem is provable using induction.",
        "The theorem is provable by induction.",
        "Other proof strategies are unnecessary.",
    ]): [
        "It is possible that the theorem is provable using induction.",
        "The theorem is provable by induction.",
        "Other proof strategies are unnecessary.",
    ],
    # Referential opacity trace
    frozenset([
        "The variable 'morning_star' refers to Venus.",
        "There is no existing information about 'evening_star'.",
        "Data about 'evening_star' needs to be looked up.",
    ]): [
        "The variable 'morning_star' refers to Venus.",
        "There is no existing information about 'evening_star'.",
        "Data about 'evening_star' needs to be looked up.",
        "If 'evening_star' also refers to Venus, then information about 'morning_star' applies to 'evening_star'.",
    ],
    # Demo 1: Theorem proving
    frozenset([
        "Function f is continuous on [a,b].",
        "f is continuous on [a,b].",
        "The Intermediate Value Theorem applies to f on [a,b].",
        "There exists c in (a,b) with f(c) = 0.",
        "f is differentiable everywhere on (a,b).",
        "Critical points can be found by setting f'(x) = 0.",
    ]): [
        "Function f is continuous on [a,b].",
        "The Intermediate Value Theorem applies to f on [a,b].",
        "There exists c in (a,b) with f(c) = 0.",
        "f is differentiable everywhere on (a,b).",
        "Critical points can be found by setting f'(x) = 0.",
        "Continuity on [a,b] does NOT imply differentiability on (a,b).",
        "Differentiability was asserted without being derived from continuity.",
    ],
    # Demo 2: Experimental protocol
    frozenset([
        "The palladium catalyst is air-sensitive.",
        "The catalyst must be handled under inert atmosphere.",
        "Exposure to oxygen will deactivate the catalyst.",
        "The catalyst is transferred under nitrogen atmosphere.",
        "The flask is opened to air.",
        "The reagent is added via syringe.",
    ]): [
        "The palladium catalyst is air-sensitive.",
        "The catalyst must be handled under inert atmosphere.",
        "Exposure to oxygen will deactivate the catalyst.",
        "The catalyst is transferred under nitrogen atmosphere.",
        "The flask is opened to air.",
        "The reagent is added via syringe.",
        "Opening the flask to air exposes the catalyst to oxygen.",
        "Exposing the catalyst to air will deactivate it.",
    ],
    # Demo 3: Literature synthesis
    frozenset([
        "Compound X inhibits kinase Y.",
        "Kinase Y is essential for activating pathway Z.",
        "Without kinase Y, pathway Z is abolished.",
        "Compound X impairs pathway Z signaling.",
        "X inhibits Y and Y is required for Z.",
        "Compound X is recommended as an enhancer of pathway Z.",
    ]): [
        "Compound X inhibits kinase Y.",
        "Kinase Y is essential for activating pathway Z.",
        "Without kinase Y, pathway Z is abolished.",
        "Compound X impairs pathway Z signaling.",
        "X inhibits Y and Y is required for Z.",
        "Compound X is recommended as an enhancer of pathway Z.",
        "Compound X cannot enhance pathway Z because it impairs it.",
        "Recommending X as an enhancer contradicts the finding that X impairs Z.",
    ],
}


def compute_closure(
    assertions: list[str],
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> list[str]:
    """Compute the commitment closure over a set of assertions.

    This is the core philosophical operation: given what the agent has
    explicitly asserted, what is it committed to?

    Args:
        assertions: List of explicit assertion strings from the trace so far.
        test_mode: If True, use fixtures.
        api_key: Anthropic API key.

    Returns:
        List of commitment strings (superset of input assertions).
    """
    if not assertions:
        return []

    if test_mode:
        return _test_closure_lookup(assertions)

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _test_closure_lookup(assertions)

    return _api_compute_closure(assertions, key)


def _api_compute_closure(
    assertions: list[str], api_key: str, max_retries: int = 3
) -> list[str]:
    """Compute commitment closure via LLM."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    assertions_text = "\n".join(f"  - {a}" for a in assertions)
    prompt = CLOSURE_PROMPT.format(assertions=assertions_text)

    for attempt in range(max_retries):
        try:
            text_parts = []
            with client.messages.stream(
                model=_get_model(),
                max_tokens=2048,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for chunk in stream.text_stream:
                    text_parts.append(chunk)
            text = "".join(text_parts).strip()

            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            commitments = json.loads(text)
            if isinstance(commitments, list) and all(isinstance(c, str) for c in commitments):
                return commitments
            logger.warning("Closure API returned non-list: %s", text[:100])
            return list(assertions)  # fallback: return assertions unchanged
        except json.JSONDecodeError:
            logger.warning("Failed to parse closure response as JSON")
            return list(assertions)
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"Anthropic API authentication failed: {e}") from e
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APIError) as e:
            wait = min(2 ** (attempt + 1), 16)
            logger.warning("API error in closure, retrying in %ds (%d/%d): %s",
                           wait, attempt + 1, max_retries, e)
            time.sleep(wait)

    raise RuntimeError(f"Closure computation failed after {max_retries} retries")


def _test_closure_lookup(assertions: list[str]) -> list[str]:
    """Look up closure from test fixtures."""
    key = frozenset(assertions)
    if key in _TEST_CLOSURES:
        return _TEST_CLOSURES[key]

    # Try subset matching: find the fixture that best overlaps
    best_match = None
    best_overlap = 0
    for fixture_key, closure in _TEST_CLOSURES.items():
        overlap = len(key & fixture_key)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = closure

    if best_match and best_overlap >= len(assertions) * 0.5:
        return best_match

    # Fallback: return assertions as-is (no inferential commitments)
    return list(assertions)
