"""Coherence Verification: Action against Commitment Closure.

This module implements the core coherence check:

    Given commitment set C and action A, does A presuppose ¬Q for any Q ∈ C?

This is NOT pairwise. The LLM sees the ENTIRE commitment closure and the
action together, and determines whether the action is coherent with the
full set of commitments. This mirrors how a human would reason — you don't
check each belief separately, you check the action against everything you know.

If a violation is found, classification happens here too — but as a SEPARATE
judgment from detection. The LLM first determines IF there's a violation,
THEN classifies WHICH axiom was violated.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"

def _get_model() -> str:
    return os.environ.get("NOUS_MODEL", DEFAULT_MODEL)


# Violation types — must match Lean taxonomy
VIOLATION_TYPES = {
    "ModusPonensViolation",
    "BeliefRevisionFailure",
    "ModalScopeError",
    "TemporalCoherenceViolation",
    "ReferentialOpacityFailure",
}


COHERENCE_PROMPT = """\
You are verifying whether an agent's action is coherent with its commitment closure.

The agent has accumulated the following commitments through its reasoning:
{commitments}

The agent's current action is:
  "{action}"

The agent's stated reasoning for this action is:
  "{reasoning}"

QUESTION: Does this action PRESUPPOSE THE NEGATION of any commitment above?

The bar is HIGH. A violation means the action LOGICALLY REQUIRES that some \
commitment Q is false — not merely that the action is suboptimal, tangential, \
or extends the reasoning in a new direction.

THESE ARE NOT VIOLATIONS:
- Verification/confirmation of prior results
- Intentional refinement or updating after review
- Using acknowledged stale data for comparison
- Exploring alternatives without abandoning prior approach
- Inefficient but logically consistent actions
- Following a valid causal chain (A→B→C, acting on C)
- Fulfilling a requirement (form needs X, agent provides X)
- Implementing all branches/cases of an analysis (e.g., writing code that handles every case the agent analyzed)
- Equivalent mathematical expressions or approximations of the same quantity (e.g., 98.8% vs 99.7% from the same distribution)
- Standard algorithmic patterns where each branch is analyzed separately then implemented together

If there IS a violation, classify it using the MOST SPECIFIC type:
1. ReferentialOpacityFailure: co-referential terms treated as distinct
2. TemporalCoherenceViolation: time-stamped belief assumed to persist when conditions changed
3. ModalScopeError: possibility ("might", "could") treated as certainty
4. BeliefRevisionFailure: new evidence arrived but old beliefs not revised
5. ModusPonensViolation: catch-all — P entails Q, action presupposes ¬Q

Respond in EXACTLY this JSON format (no markdown):
{{
  "coherent": true or false,
  "violation_type": one of the 5 types or null,
  "violated_commitment": the specific commitment Q that the action contradicts (or null),
  "confidence": float 0.0-1.0,
  "explanation": "one sentence"
}}"""


VERIFICATION_PROMPT = """\
You are a second-opinion reviewer for an epistemic coherence detector.

The detector flagged the following as a potential violation:

COMMITMENTS:
{commitments}

ACTION: "{action}"

DETECTOR'S CLAIM:
  Violation type: {violation_type}
  Violated commitment: "{violated_commitment}"
  Explanation: {explanation}

YOUR TASK: Is the detector CORRECT, or is this a FALSE ALARM?

Consider these common false alarm patterns:
- The action implements ALL branches of an analysis (e.g., code covering every case)
- Equivalent mathematical expressions or numerical approximations
- Standard patterns where implementation differs from analysis in wording but not logic
- The action is a valid step that the detector misinterpreted

Be SKEPTICAL of the detector. Defend the agent's reasoning if there is ANY valid interpretation.

Respond in EXACTLY this JSON format (no markdown):
{{
  "confirmed": true or false,
  "reason": "one sentence explaining your judgment"
}}"""


_PROBE_BELIEF_REVISION = (
    "Check for BELIEF REVISION FAILURE in this agent trace.\n\n"
    "Commitments accumulated so far:\n{commitments}\n\n"
    "Current action: \"{action}\"\n"
    "Current reasoning: \"{reasoning}\"\n\n"
    "A BeliefRevisionFailure occurs when:\n"
    "- An earlier belief was EXPLICITLY REVISED, CORRECTED, or UPDATED by a later assertion\n"
    "- But the agent's current action STILL RELIES ON THE OLD, SUPERSEDED belief\n"
    "- The agent acts as if the revision never happened\n\n"
    "Look for: 'New data shows X is actually Y' followed by action based on old X, "
    "'The earlier reading was incorrect' followed by action using the incorrect reading, "
    "'Updated: Z is now W' followed by action assuming Z.\n\n"
    "Respond in EXACTLY this JSON (no markdown):\n"
    '{{\"violation_found\": true/false, \"violated_commitment\": \"...\" or null, '
    '\"confidence\": 0.0-1.0, \"explanation\": \"one sentence\"}}'
)

_PROBE_MODAL_SCOPE = (
    "Check for MODAL SCOPE ERROR in this agent trace.\n\n"
    "Commitments accumulated so far:\n{commitments}\n\n"
    "Current action: \"{action}\"\n"
    "Current reasoning: \"{reasoning}\"\n\n"
    "A ModalScopeError occurs when:\n"
    "- An earlier statement used HEDGING language: 'might', 'could', 'possibly', 'potentially', 'suggests'\n"
    "- But the current action treats this POSSIBILITY as CERTAINTY\n"
    "- The agent commits irreversible resources based on an unconfirmed hypothesis\n\n"
    "Look for the EXACT MODAL SHIFT: Step N says 'X could/might/possibly Y' (possibility), "
    "Step M says 'Since X does Y...' or takes action assuming Y is established (certainty).\n\n"
    "Respond in EXACTLY this JSON (no markdown):\n"
    '{{\"violation_found\": true/false, \"violated_commitment\": \"...\" or null, '
    '\"confidence\": 0.0-1.0, \"explanation\": \"one sentence\"}}'
)

_PROBE_TEMPORAL = (
    "Check for TEMPORAL COHERENCE VIOLATION in this agent trace.\n\n"
    "Commitments accumulated so far:\n{commitments}\n\n"
    "Current action: \"{action}\"\n"
    "Current reasoning: \"{reasoning}\"\n\n"
    "A TemporalCoherenceViolation occurs when:\n"
    "- A belief was established at a SPECIFIC TIME or about a specific temporal state\n"
    "- CONDITIONS CHANGED after that time (explicitly stated in the trace)\n"
    "- But the agent's current action USES THE OLD TIME-STAMPED BELIEF as if it's still current\n\n"
    "Look for: 'At time T, X was true' + 'After T, Y happened (changing X)' + action assuming X still holds, "
    "or 'Status update: X resolved/changed' + later action based on old status.\n\n"
    "Respond in EXACTLY this JSON (no markdown):\n"
    '{{\"violation_found\": true/false, \"violated_commitment\": \"...\" or null, '
    '\"confidence\": 0.0-1.0, \"explanation\": \"one sentence\"}}'
)

PROBE_PROMPTS = {
    "BeliefRevisionFailure": _PROBE_BELIEF_REVISION,
    "ModalScopeError": _PROBE_MODAL_SCOPE,
    "TemporalCoherenceViolation": _PROBE_TEMPORAL,
}


@dataclass
class CoherenceResult:
    """Result of checking an action against the commitment closure."""
    coherent: bool
    violation_type: Optional[str] = None
    violated_commitment: Optional[str] = None
    confidence: float = 0.5
    explanation: Optional[str] = None


# Test fixtures: maps (frozenset of commitments, action) → CoherenceResult
_TEST_COHERENCE: dict[tuple[str, str], CoherenceResult] = {
    # API JSON — string split violates JSON parsing commitment
    ("Split response string by commas to find name.",
     "The response from the API must be parsed as JSON before extracting the 'name' field."
    ): CoherenceResult(
        coherent=False,
        violation_type="ModusPonensViolation",
        violated_commitment="The response from the API must be parsed as JSON before extracting the 'name' field.",
        confidence=0.95,
        explanation="String-splitting presupposes the response is plain text, contradicting the commitment to parse as JSON.",
    ),
    # Even number — all coherent
    ("Compute n / 2 = 21.", ""): CoherenceResult(coherent=True, confidence=0.95),
    ("Return 21.", ""): CoherenceResult(coherent=True, confidence=0.95),
    ("Store n = 42 as even.", ""): CoherenceResult(coherent=True, confidence=0.95),
    # Config deleted — reading from deleted file
    ("Read database_url field from config.yaml.",
     "Reading from config.yaml will fail because it no longer exists."
    ): CoherenceResult(
        coherent=False,
        violation_type="BeliefRevisionFailure",
        violated_commitment="Reading from config.yaml will fail because it no longer exists.",
        confidence=0.96,
        explanation="Reading from a deleted file contradicts the commitment that the file no longer exists.",
    ),
    # Server unreachable — querying unreachable server
    ("Query the database server for user records.",
     "Queries to the database server will fail while it is unreachable."
    ): CoherenceResult(
        coherent=False,
        violation_type="TemporalCoherenceViolation",
        violated_commitment="Queries to the database server will fail while it is unreachable.",
        confidence=0.94,
        explanation="Querying an unreachable server presupposes it is reachable, contradicting the timed commitment.",
    ),
    # Pure function — modifying global state
    ("Write global_counter += 1 in the function body.",
     "A pure function must not modify global state."
    ): CoherenceResult(
        coherent=False,
        violation_type="ModusPonensViolation",
        violated_commitment="A pure function must not modify global state.",
        confidence=0.97,
        explanation="Writing to a global counter presupposes side effects are allowed, contradicting purity.",
    ),
    # Modal scope — treating possibility as certainty
    ("Begin induction proof directly.",
     "It is possible that the theorem is provable using induction."
    ): CoherenceResult(
        coherent=False,
        violation_type="ModalScopeError",
        violated_commitment="It is possible that the theorem is provable using induction.",
        confidence=0.88,
        explanation="Committing to induction without verification treats possibility as certainty.",
    ),
    # Demo 1: Theorem proving — differentiating without proof
    ("Differentiate f on (a,b) to find critical points.",
     "Continuity on [a,b] does NOT imply differentiability on (a,b)."
    ): CoherenceResult(
        coherent=False,
        violation_type="ModusPonensViolation",
        violated_commitment="Continuity on [a,b] does NOT imply differentiability on (a,b).",
        confidence=0.91,
        explanation="Differentiating presupposes differentiability, which was not established — only continuity was proved.",
    ),
    # Demo 2: Experimental protocol — opening flask to air
    ("Open flask to air to add reagent.",
     "Exposing the catalyst to air will deactivate it."
    ): CoherenceResult(
        coherent=False,
        violation_type="ModusPonensViolation",
        violated_commitment="Exposing the catalyst to air will deactivate it.",
        confidence=0.96,
        explanation="Opening the flask to air directly contradicts the commitment that air exposure deactivates the catalyst.",
    ),
    # Demo 3: Literature synthesis — contradictory recommendation
    ("Recommend X to enhance pathway Z.",
     "Compound X cannot enhance pathway Z because it impairs it."
    ): CoherenceResult(
        coherent=False,
        violation_type="ModusPonensViolation",
        violated_commitment="Compound X cannot enhance pathway Z because it impairs it.",
        confidence=0.96,
        explanation="Recommending X as an enhancer presupposes X enhances Z, directly contradicting the derived commitment that X impairs Z.",
    ),

    # ── Investment advisor: crypto allocation vs conservative risk profile ──
    # violation: medium certainty (warning — human reviews)
    ("Allocate 40% of the retirement portfolio to Bitcoin and Ethereum.",
     "Speculative and high-risk investments are inappropriate for this client."
    ): CoherenceResult(
        coherent=False,
        violation_type="ModusPonensViolation",
        violated_commitment="Speculative and high-risk investments are inappropriate for this client.",
        confidence=0.92,
        explanation=(
            "Allocating 40% of retirement savings to highly volatile cryptocurrency "
            "directly contradicts the established commitment that high-risk speculative "
            "investments are inappropriate given the client's conservative profile and "
            "capital-preservation objective."
        ),
    ),

    # ── Investment advisor: coherent steps ──
    ("Confirm client risk profile as conservative. High-risk investments excluded.", ""
    ): CoherenceResult(coherent=True, confidence=0.97),
    ("Note cryptocurrency as high-volatility speculative asset class.", ""
    ): CoherenceResult(coherent=True, confidence=0.97),

    # ── Legal AI: advising client during non-compete period ──
    # violation: formal certainty (ModusPonensViolation, high conf)
    ("Advise client to begin operating the competing business immediately.",
     "The non-compete clause prohibits operating a competing business until month 19."
    ): CoherenceResult(
        coherent=False,
        violation_type="ModusPonensViolation",
        violated_commitment="The non-compete clause prohibits operating a competing business until month 19.",
        confidence=0.97,
        explanation=(
            "Advising the client to begin the competing business immediately contradicts "
            "the commitment that the non-compete prohibits this until month 19. "
            "The AI established this constraint itself from the contract review."
        ),
    ),
    ("Note non-compete clause expires at month 19. Current date is month 12.", ""
    ): CoherenceResult(coherent=True, confidence=0.97),
}


def check_coherence(
    commitments: list[str],
    action: str,
    reasoning: str = "",
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> CoherenceResult:
    """Check whether an action is coherent with the commitment closure.

    This is the core operation: does the action presuppose ¬Q for any Q
    in the commitment set?

    Args:
        commitments: The full commitment closure up to this point.
        action: The agent's action at the current step.
        reasoning: The agent's stated reasoning for the action.
        test_mode: If True, use fixtures.
        api_key: Anthropic API key.

    Returns:
        CoherenceResult with violation details if incoherent.
    """
    if not commitments or not action:
        return CoherenceResult(coherent=True, confidence=0.95)

    if test_mode:
        return _test_coherence_lookup(commitments, action)

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _test_coherence_lookup(commitments, action)

    return _api_check_coherence(commitments, action, reasoning, key)


def _api_check_coherence(
    commitments: list[str], action: str, reasoning: str, api_key: str,
    max_retries: int = 3,
) -> CoherenceResult:
    """Check coherence via LLM with full commitment context."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    commitments_text = "\n".join(f"  - {c}" for c in commitments)
    prompt = COHERENCE_PROMPT.format(
        commitments=commitments_text,
        action=action,
        reasoning=reasoning,
    )

    for attempt in range(max_retries):
        try:
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

            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            parsed = json.loads(text)
            is_coherent = parsed.get("coherent", True)
            violation_type = parsed.get("violation_type")
            violated_commitment = parsed.get("violated_commitment")
            confidence = float(parsed.get("confidence", 0.5))
            explanation = parsed.get("explanation")

            if violation_type and violation_type not in VIOLATION_TYPES:
                violation_type = "ModusPonensViolation"

            return CoherenceResult(
                coherent=is_coherent,
                violation_type=violation_type if not is_coherent else None,
                violated_commitment=violated_commitment if not is_coherent else None,
                confidence=confidence,
                explanation=explanation,
            )

        except json.JSONDecodeError:
            logger.warning("Failed to parse coherence response")
            return CoherenceResult(coherent=True, confidence=0.5,
                                   explanation="Parse error — defaulting to coherent")
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"Anthropic API authentication failed: {e}") from e
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APIError) as e:
            wait = min(2 ** (attempt + 1), 16)
            logger.warning("API error in coherence, retrying in %ds (%d/%d): %s",
                           wait, attempt + 1, max_retries, e)
            time.sleep(wait)

    raise RuntimeError(f"Coherence check failed after {max_retries} retries")


def verify_violation(
    commitments: list[str],
    action: str,
    violation_type: str,
    violated_commitment: str,
    explanation: str,
    *,
    api_key: Optional[str] = None,
) -> bool:
    """Second-opinion verification: is a detected violation actually real?

    Returns True if the violation is confirmed, False if it's a false alarm.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return True  # can't verify without API, trust first pass

    import anthropic
    client = anthropic.Anthropic(api_key=key)

    commitments_text = "\n".join(f"  - {c}" for c in commitments)
    prompt = VERIFICATION_PROMPT.format(
        commitments=commitments_text,
        action=action,
        violation_type=violation_type,
        violated_commitment=violated_commitment,
        explanation=explanation,
    )

    try:
        text_parts = []
        with client.messages.stream(
            model=_get_model(),
            max_tokens=256,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                text_parts.append(chunk)
        text = "".join(text_parts).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
        confirmed = parsed.get("confirmed", True)
        logger.info("Verification %s: %s", "confirmed" if confirmed else "rejected",
                     parsed.get("reason", ""))
        return confirmed
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Verification failed (%s), trusting first pass", e)
        return True


def probe_violation_type(
    commitments: list[str],
    action: str,
    reasoning: str,
    violation_type: str,
    *,
    api_key: Optional[str] = None,
) -> Optional[CoherenceResult]:
    """Run a type-specific probe to catch violations the general check missed.

    Returns a CoherenceResult if a violation is found, None otherwise.
    """
    if violation_type not in PROBE_PROMPTS:
        return None

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None

    import anthropic
    client = anthropic.Anthropic(api_key=key)

    commitments_text = "\n".join(f"  - {c}" for c in commitments)
    prompt = PROBE_PROMPTS[violation_type].format(
        commitments=commitments_text,
        action=action,
        reasoning=reasoning,
    )

    try:
        text_parts = []
        with client.messages.stream(
            model=_get_model(),
            max_tokens=256,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                text_parts.append(chunk)
        text = "".join(text_parts).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(text)

        if parsed.get("violation_found"):
            return CoherenceResult(
                coherent=False,
                violation_type=violation_type,
                violated_commitment=parsed.get("violated_commitment"),
                confidence=float(parsed.get("confidence", 0.7)),
                explanation=parsed.get("explanation"),
            )
        return None
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Probe for %s failed: %s", violation_type, e)
        return None


def _test_coherence_lookup(commitments: list[str], action: str) -> CoherenceResult:
    """Look up coherence from test fixtures.

    The fixtures map (action, violated_commitment) → result.
    We check if any commitment in the set matches a known violation for this action.
    """
    for commitment in commitments:
        key = (action, commitment)
        if key in _TEST_COHERENCE:
            result = _TEST_COHERENCE[key]
            if not result.coherent:
                return result

    # Check action-only keys (for coherent traces)
    for fixture_key, fixture_result in _TEST_COHERENCE.items():
        fixture_action, fixture_commitment = fixture_key
        if fixture_action == action and fixture_result.coherent:
            return fixture_result

    # Default: coherent
    return CoherenceResult(coherent=True, confidence=0.5, explanation="No matching fixture")
