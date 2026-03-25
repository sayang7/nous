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

# Default model for API calls. Can be overridden via CLOSUREGUARD_MODEL env var.
DEFAULT_MODEL = "claude-sonnet-4-6"

def _get_model() -> str:
    return os.environ.get("CLOSUREGUARD_MODEL", DEFAULT_MODEL)

# Violation types matching the Lean taxonomy
VIOLATION_TYPES = {
    "ModusPonensViolation",
    "BeliefRevisionFailure",
    "ModalScopeError",
    "TemporalCoherenceViolation",
    "ReferentialOpacityFailure",
}

COHERENCE_CHECK_PROMPT = """\
You are an axiom-guided epistemic closure violation detector. Apply the \
following formal axiom tests to determine whether a subsequent action \
contradicts a commitment entailed by a prior belief.

Prior belief: {belief_a}
Subsequent action or belief: {belief_b}
{trace_context}
Apply each axiom test IN ORDER. For each test, check whether it applies \
BEFORE moving to the next. Classify with the MOST SPECIFIC type that fits:

1. REFERENTIAL OPACITY (check FIRST — most specific):
   K(a=b) does not permit free substitution in epistemic contexts.
   TRIGGER: Two names/terms/identifiers/variables refer to the same entity, \
but the agent treats them as distinct. OR the agent substitutes freely in \
a belief context where substitution is not valid.
   EXAMPLES: "morning_star = evening_star" but agent says "no data on evening_star"; \
"user.email = contact_email" but agent queries both separately; property aliasing.
   If this pattern matches → ReferentialOpacityFailure.

2. TEMPORAL INDEXING (check SECOND — time-specific):
   Beliefs are indexed to times; K_t(P) does not entail K_t'(P) when \
conditions change.
   TRIGGER: The prior belief is explicitly or implicitly time-stamped \
(mentions "as of", "at [time]", "currently", "last checked", "was"), \
AND the action assumes the same state persists at a later time when \
conditions may have changed. Time-sensitive domains: prices, server status, \
inventory, weather, permissions, session state.
   If this pattern matches → TemporalCoherenceViolation.

3. MODAL SCOPE (◇ vs □):
   Possibility (◇P) does not entail necessity (□P).
   TRIGGER: The prior belief uses hedging language ("might", "could", \
"possibly", "it is possible that", "may", "potentially", "suggests") \
AND the action treats it as certain (commits to one path, rules out \
alternatives, acts definitively).
   If this pattern matches → ModalScopeError.

4. AGM BELIEF REVISION:
   When new evidence ¬P arrives, all beliefs depending on P must be revised.
   TRIGGER: The prior belief is the NEW evidence that invalidates an \
OLDER belief, and the action still relies on the old (now-invalidated) \
belief. Key signal: the temporal order matters — the belief represents \
learning something new, but the action ignores that learning.
   If this pattern matches → BeliefRevisionFailure.

5. AXIOM K (Modus Ponens Closure) — CATCH-ALL:
   K(P) ∧ K(P→Q) → K(Q). Does the prior belief P logically entail Q, \
and does the action presuppose ¬Q?
   Use ModusPonensViolation ONLY if none of the above more specific \
types apply. This is the general case.

IMPORTANT: Only judge VIOLATION if an axiom test CLEARLY and UNAMBIGUOUSLY fails. \
Default to COHERENT. The bar for VIOLATION is HIGH — the action must PRESUPPOSE \
THE NEGATION of a commitment entailed by the prior belief. Mere tension, tangential \
relevance, or extending beliefs in a new direction is NEVER a violation.

CRITICAL EXCEPTIONS — these are NOT violations:
- VERIFICATION: Computing a result then checking/confirming it is coherent. \
  Solving x=5 then verifying 5+5=10 is NOT a violation.
- INTENTIONAL REFINEMENT: Updating, refactoring, or improving after stating \
current state. Describing current code then rewriting it is correct belief revision. \
  "Function does X" then "Rewrite function to do Y" → COHERENT.
- HISTORICAL REFERENCE: Using "last known", "as of [time]", or "yesterday" data \
for comparison or reporting is temporally coherent WHEN the staleness is acknowledged. \
  "Price was $47 at market close yesterday" then "Report price as $47 (market closed)" → COHERENT.
- CONDITIONAL EXPLORATION: Exploring alternatives does not contradict prior approach.
- SUBOPTIMAL BUT CONSISTENT: Inefficient but not logically contradictory → COHERENT.
- VALID CAUSAL CHAINS: If belief A causes/implies B, and B causes/implies C, \
then acting on C is COHERENT — it follows from the chain. \
  "Gene X is mutated" → "X impairs repair" → "Try therapy targeting repair defect" → COHERENT.
- FILLING IN DETAILS: Providing information that a form/process requires is NOT \
contradicting the requirement — it is fulfilling it. \
  "Form requires passenger details" then "Enter passenger details" → COHERENT.
- USING PRIOR RESULTS: Referring back to a computed value or established fact for \
further reasoning is coherent, not contradictory. \
  "x = 5" then "Since x = 5, compute 2x = 10" → COHERENT.

Respond in EXACTLY this JSON format (no markdown):
{{
  "judgment": "VIOLATION" or "COHERENT",
  "violation_type": one of ["ModusPonensViolation", "BeliefRevisionFailure", \
"ModalScopeError", "TemporalCoherenceViolation", "ReferentialOpacityFailure"] \
or null if coherent,
  "confidence": float between 0.0 and 1.0,
  "explanation": "one sentence citing which axiom test failed and why"
}}"""

BATCH_COHERENCE_CHECK_PROMPT = """\
You are an axiom-guided epistemic closure violation detector. For each \
numbered belief-action pair below, apply the formal axiom tests to determine \
whether the action contradicts a commitment entailed by the prior belief.

AXIOM TESTS — apply in order, classify with the MOST SPECIFIC type:
1. REFERENTIAL OPACITY (ReferentialOpacityFailure): two names/terms refer to the same entity \
but agent treats them as distinct, or substitutes freely in an opaque epistemic context
2. TEMPORAL INDEX (TemporalCoherenceViolation): belief is time-stamped ("as of", "at [time]", \
"currently", "was"), action assumes same state at a later time when conditions changed
3. MODAL SCOPE (ModalScopeError): belief uses hedging ("might", "could", "possibly"), \
action treats it as certain
4. AGM REVISION (BeliefRevisionFailure): belief IS new evidence invalidating an older belief, \
action still relies on the old (now-invalidated) belief
5. AXIOM K (ModusPonensViolation): CATCH-ALL — P entails Q, action presupposes NOT-Q. \
Use ONLY if none of the above specific types apply

Default to COHERENT unless an axiom CLEARLY and UNAMBIGUOUSLY fails. \
The bar is HIGH — the action must PRESUPPOSE THE NEGATION of a commitment.

CRITICAL EXCEPTIONS — these are NOT violations:
- VERIFICATION: Computing then checking/confirming a result is coherent.
- INTENTIONAL REFINEMENT: Describing current state then updating/refactoring is correct revision.
- HISTORICAL REFERENCE: Using "as of [time]"/"yesterday" data for reporting is coherent when acknowledged.
- CONDITIONAL EXPLORATION: Exploring alternatives does not contradict prior approach.
- SUBOPTIMAL BUT CONSISTENT: Inefficient but not contradictory → COHERENT.
- VALID CAUSAL CHAINS: A→B→C reasoning where acting on C follows from the chain is COHERENT.
- FILLING IN DETAILS: Providing what a form/process requires is fulfilling, not contradicting.
- USING PRIOR RESULTS: Referring back to established facts for further reasoning is COHERENT.

PAIRS:
{pairs_text}

Respond with EXACTLY a JSON array (no markdown), one object per pair in order:
[
  {{
    "pair_index": 0,
    "judgment": "VIOLATION" or "COHERENT",
    "violation_type": one of the five types or null,
    "confidence": float 0.0-1.0,
    "explanation": "one sentence citing which axiom failed"
  }},
  ...
]"""


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

    # ── Demo 1: Theorem Proving — continuity does NOT imply differentiability ──
    ("Function f is continuous on [a,b].",
     "Differentiate f on (a,b) to find critical points."
     ): EntailmentResult(False, 0.91, "ModusPonensViolation",
        "Continuity does not imply differentiability; the agent assumed differentiability without proof."),
    ("f is continuous on [a,b].",
     "Differentiate f on (a,b) to find critical points."
     ): EntailmentResult(False, 0.90, "ModusPonensViolation",
        "Continuity does not imply differentiability; differentiating requires a separate proof."),
    ("The Intermediate Value Theorem applies to f on [a,b].",
     "Differentiate f on (a,b) to find critical points."
     ): EntailmentResult(True, 0.5),
    ("There exists c in (a,b) with f(c) = 0.",
     "Differentiate f on (a,b) to find critical points."
     ): EntailmentResult(True, 0.5),
    ("Function f is continuous on [a,b].",
     "Apply IVT to find root c."
     ): EntailmentResult(True, 0.93),
    ("f is continuous on [a,b].",
     "Apply IVT to find root c."
     ): EntailmentResult(True, 0.93),
    ("f is differentiable everywhere on (a,b).",
     "Differentiate f on (a,b) to find critical points."
     ): EntailmentResult(True, 0.95),
    ("Function f is continuous on [a,b].",
     "Record f as continuous on [a,b]."
     ): EntailmentResult(True, 0.95),
    ("f is continuous on [a,b].",
     "Record f as continuous on [a,b]."
     ): EntailmentResult(True, 0.95),
    ("Critical points can be found by setting f'(x) = 0.",
     "Differentiate f on (a,b) to find critical points."
     ): EntailmentResult(True, 0.94),

    # ── Demo 2: Experimental Protocol — opening flask violates inert atmosphere ──
    ("The palladium catalyst is air-sensitive.",
     "Open flask to air to add reagent."
     ): EntailmentResult(False, 0.95, "ModusPonensViolation",
        "Opening flask to air contradicts the requirement for inert atmosphere with air-sensitive catalyst."),
    ("The catalyst must be handled under inert atmosphere.",
     "Open flask to air to add reagent."
     ): EntailmentResult(False, 0.96, "ModusPonensViolation",
        "Opening to air directly violates the stated inert atmosphere requirement."),
    ("Exposure to oxygen will deactivate the catalyst.",
     "Open flask to air to add reagent."
     ): EntailmentResult(False, 0.94, "ModusPonensViolation",
        "Exposing to air introduces oxygen, which the agent stated would deactivate the catalyst."),
    ("The catalyst is transferred under nitrogen atmosphere.",
     "Open flask to air to add reagent."
     ): EntailmentResult(False, 0.88, "ModusPonensViolation",
        "Opening to air negates the nitrogen atmosphere established in the prior step."),
    ("The palladium catalyst is air-sensitive.",
     "Transfer catalyst to reaction vessel under N2."
     ): EntailmentResult(True, 0.94),
    ("The catalyst must be handled under inert atmosphere.",
     "Transfer catalyst to reaction vessel under N2."
     ): EntailmentResult(True, 0.95),
    ("Exposure to oxygen will deactivate the catalyst.",
     "Transfer catalyst to reaction vessel under N2."
     ): EntailmentResult(True, 0.93),
    ("The palladium catalyst is air-sensitive.",
     "Note catalyst handling requirement: inert atmosphere only."
     ): EntailmentResult(True, 0.95),
    ("The catalyst must be handled under inert atmosphere.",
     "Note catalyst handling requirement: inert atmosphere only."
     ): EntailmentResult(True, 0.96),
    ("Exposure to oxygen will deactivate the catalyst.",
     "Note catalyst handling requirement: inert atmosphere only."
     ): EntailmentResult(True, 0.93),
    ("The catalyst is transferred under nitrogen atmosphere.",
     "Transfer catalyst to reaction vessel under N2."
     ): EntailmentResult(True, 0.95),

    # ── Demo 3: Literature Synthesis — recommendation contradicts synthesis ──
    ("Compound X impairs pathway Z signaling.",
     "Recommend X to enhance pathway Z."
     ): EntailmentResult(False, 0.96, "ModusPonensViolation",
        "Recommending X as enhancer directly contradicts the stated finding that X impairs pathway Z."),
    ("X inhibits Y and Y is required for Z.",
     "Recommend X to enhance pathway Z."
     ): EntailmentResult(False, 0.93, "ModusPonensViolation",
        "If X inhibits Y and Y is required for Z, X cannot enhance Z."),
    ("Compound X inhibits kinase Y.",
     "Recommend X to enhance pathway Z."
     ): EntailmentResult(True, 0.5),
    ("Kinase Y is essential for activating pathway Z.",
     "Recommend X to enhance pathway Z."
     ): EntailmentResult(True, 0.5),
    ("Without kinase Y, pathway Z is abolished.",
     "Recommend X to enhance pathway Z."
     ): EntailmentResult(True, 0.5),
    ("Compound X inhibits kinase Y.",
     "Record: X inhibits kinase Y (IC50=12nM)."
     ): EntailmentResult(True, 0.96),
    ("Kinase Y is essential for activating pathway Z.",
     "Record: kinase Y required for pathway Z activation."
     ): EntailmentResult(True, 0.95),
    ("Without kinase Y, pathway Z is abolished.",
     "Record: kinase Y required for pathway Z activation."
     ): EntailmentResult(True, 0.93),
    ("Compound X impairs pathway Z signaling.",
     "Conclude: X impairs pathway Z."
     ): EntailmentResult(True, 0.97),
    ("X inhibits Y and Y is required for Z.",
     "Conclude: X impairs pathway Z."
     ): EntailmentResult(True, 0.94),
    ("Compound X inhibits kinase Y.",
     "Conclude: X impairs pathway Z."
     ): EntailmentResult(True, 0.5),
    ("Kinase Y is essential for activating pathway Z.",
     "Conclude: X impairs pathway Z."
     ): EntailmentResult(True, 0.5),
    ("Without kinase Y, pathway Z is abolished.",
     "Conclude: X impairs pathway Z."
     ): EntailmentResult(True, 0.5),
    ("Compound X is recommended as an enhancer of pathway Z.",
     "Recommend X to enhance pathway Z."
     ): EntailmentResult(True, 0.95),
}


def check_entailment(
    belief_a: str,
    belief_b: str,
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
    trace_context: Optional[list[dict]] = None,
) -> EntailmentResult:
    """Check whether a prior belief and subsequent action/belief are coherent.

    Args:
        belief_a: The prior belief/commitment.
        belief_b: The subsequent belief or action description.
        test_mode: If True, use hardcoded rules instead of API.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        trace_context: Optional list of surrounding trace steps for context.
            Each dict should have 'step', 'text', and 'action' keys.

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
            result = _api_coherence_check(belief_a, belief_b, key, trace_context=trace_context)

    _cache[cache_key] = result
    return result


def clear_cache() -> None:
    """Clear the entailment cache."""
    _cache.clear()


def _format_trace_context(trace_context: Optional[list[dict]]) -> str:
    """Format trace context into a string for the prompt."""
    if not trace_context:
        return ""
    lines = ["\nSurrounding trace context (for reference — judge ONLY the pair above):"]
    for step in trace_context:
        step_num = step.get("step", "?")
        text = step.get("text", "")
        action = step.get("action", "")
        lines.append(f"  Step {step_num}: \"{text}\" → Action: \"{action}\"")
    lines.append("")
    return "\n".join(lines)


def _api_coherence_check(
    belief_a: str, belief_b: str, api_key: str, max_retries: int = 3,
    trace_context: Optional[list[dict]] = None,
) -> EntailmentResult:
    """Check belief-action coherence using Claude API with structured output."""
    import anthropic
    import time

    client = anthropic.Anthropic(api_key=api_key)
    context_str = _format_trace_context(trace_context)
    prompt = COHERENCE_CHECK_PROMPT.format(
        belief_a=belief_a, belief_b=belief_b, trace_context=context_str
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            # Use streaming to avoid "Streaming is required for long operations" error
            text_parts = []
            with client.messages.stream(
                model=_get_model(),
                max_tokens=512,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for chunk in stream.text_stream:
                    text_parts.append(chunk)
            text = "".join(text_parts).strip()
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


def check_entailment_batch(
    pairs: list[tuple[str, str]],
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> list[EntailmentResult]:
    """Check multiple belief-action pairs in a single API call.

    Args:
        pairs: List of (prior_belief, action_or_belief) tuples.
        test_mode: If True, use hardcoded rules instead of API.
        api_key: Anthropic API key.

    Returns:
        List of EntailmentResult, one per pair, in order.
    """
    if not pairs:
        return []

    # Check cache first, identify which pairs need API calls
    results: list[Optional[EntailmentResult]] = [None] * len(pairs)
    uncached_indices: list[int] = []

    for i, (a, b) in enumerate(pairs):
        cache_key = (a, b)
        if cache_key in _cache:
            results[i] = _cache[cache_key]
        else:
            uncached_indices.append(i)

    # If all cached, return immediately
    if not uncached_indices:
        return results  # type: ignore[return-value]

    uncached_pairs = [(pairs[i][0], pairs[i][1]) for i in uncached_indices]

    if test_mode:
        for idx, (a, b) in zip(uncached_indices, uncached_pairs):
            result = _test_entailment_lookup(a, b)
            _cache[(a, b)] = result
            results[idx] = result
    else:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            for idx, (a, b) in zip(uncached_indices, uncached_pairs):
                result = _test_entailment_lookup(a, b)
                _cache[(a, b)] = result
                results[idx] = result
        else:
            batch_results = _api_coherence_check_batch(uncached_pairs, key)
            for idx, (a, b), result in zip(uncached_indices, uncached_pairs, batch_results):
                _cache[(a, b)] = result
                results[idx] = result

    return results  # type: ignore[return-value]


def _api_coherence_check_batch(
    pairs: list[tuple[str, str]], api_key: str, max_retries: int = 3
) -> list[EntailmentResult]:
    """Check multiple belief-action pairs in a single API call.

    Uses streaming to avoid timeout errors on long responses.
    """
    import anthropic
    import time

    client = anthropic.Anthropic(api_key=api_key)

    # Build pairs text
    lines = []
    for i, (a, b) in enumerate(pairs):
        lines.append(f"[{i}] Prior belief: {a}")
        lines.append(f"    Subsequent: {b}")
    pairs_text = "\n".join(lines)
    prompt = BATCH_COHERENCE_CHECK_PROMPT.format(pairs_text=pairs_text)

    last_error = None
    for attempt in range(max_retries):
        try:
            # Use streaming to avoid "Streaming is required for long operations" error
            text_parts = []
            with client.messages.stream(
                model=_get_model(),
                max_tokens=512 * len(pairs),
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for chunk in stream.text_stream:
                    text_parts.append(chunk)
            text = "".join(text_parts).strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            parsed = json.loads(text)
            if not isinstance(parsed, list):
                logger.warning("Batch response is not a list, falling back to single calls")
                return [_api_coherence_check(a, b, api_key) for a, b in pairs]

            results: list[EntailmentResult] = []
            for i, (a, b) in enumerate(pairs):
                if i < len(parsed):
                    entry = parsed[i]
                    judgment = entry.get("judgment", "COHERENT").upper()
                    is_coherent = judgment == "COHERENT"
                    violation_type = entry.get("violation_type")
                    confidence = float(entry.get("confidence", 0.5))
                    explanation = entry.get("explanation")
                    if violation_type and violation_type not in VIOLATION_TYPES:
                        violation_type = "ModusPonensViolation"
                    results.append(EntailmentResult(
                        entails=is_coherent,
                        confidence=confidence,
                        violation_type=violation_type if not is_coherent else None,
                        explanation=explanation,
                    ))
                else:
                    # API returned fewer results, fall back for this pair
                    results.append(_api_coherence_check(a, b, api_key))
            return results

        except json.JSONDecodeError:
            logger.warning("Failed to parse batch response, falling back to single calls")
            return [_api_coherence_check(a, b, api_key) for a, b in pairs]
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

    raise RuntimeError(f"Batch API failed after {max_retries} retries: {last_error}")


def _test_entailment_lookup(belief_a: str, belief_b: str) -> EntailmentResult:
    """Look up entailment from hardcoded test pairs."""
    key = (belief_a, belief_b)
    if key in _TEST_ENTAILMENTS:
        return _TEST_ENTAILMENTS[key]
    # Default: coherent (no violation detected in test mode for unknown pairs)
    return EntailmentResult(entails=True, confidence=0.5, explanation="No matching fixture")
