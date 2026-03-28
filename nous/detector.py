"""Main violation detection pipeline.

Implements the philosophical funnel from Kripke semantics:

    Agent Trace
        ↓
    [1] ASSERTION EXTRACTION — what did the agent literally say?
        ↓
    [2] COMMITMENT CLOSURE — what is the agent committed to?
        C(P) ∧ C(P→Q) → C(Q)
        ↓
    [3] COHERENCE VERIFICATION — does the action presuppose ¬Q for any Q ∈ C?
        One check per action against the ENTIRE commitment set.
        ↓
    [4] VIOLATION CLASSIFICATION — which axiom failed?

This is NOT pairwise. Each action is checked against the full cumulative
commitment closure — the way a human would reason about coherence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from nous.extractor import extract_beliefs
from nous.closure import compute_closure
from nous.coherence import check_coherence, verify_violation, probe_violation_type, PROBE_PROMPTS


# Violation types — must match Lean taxonomy exactly
VIOLATION_TYPES = [
    "ModusPonensViolation",
    "BeliefRevisionFailure",
    "ModalScopeError",
    "TemporalCoherenceViolation",
    "ReferentialOpacityFailure",
]

# Minimum confidence to flag as a definite violation
CONFIDENCE_THRESHOLD = 0.85

# Violations between these thresholds are flagged as "review recommended"
REVIEW_THRESHOLD = 0.70


@dataclass
class ClosureViolationReport:
    """A detected closure violation in a reasoning trace."""

    step_index: int
    antecedent: str       # the violated commitment
    entailed: str         # explanation of the violation
    action: str           # the incoherent action
    violation_type: str   # from the 5-type taxonomy
    confidence: float
    needs_review: bool = False  # True if confidence is in the review band


_MODAL_SIGNALS = {"might", "could", "possibly", "potentially", "suggests", "may", "perhaps", "likely"}
_TEMPORAL_SIGNALS = {"updated", "now", "later", "changed", "resolved", "new data", "repeat", "revised",
                     "no longer", "previously", "earlier", "at ", "as of"}
_REVISION_SIGNALS = {"actually", "corrected", "revised", "updated", "normalized", "false",
                     "spurious", "incorrect", "turns out", "now shows", "new reading"}


def _select_probes(
    cumulative_assertions: list[str], step_text: str, step_action: str,
) -> list[str]:
    """Select which type-specific probes to run based on textual signals.

    Only triggers probes when there are lexical hints that a specific violation
    type MIGHT be present. This keeps API costs low — typically 0-1 extra calls
    per step instead of 3.
    """
    probes = []
    all_text = " ".join(cumulative_assertions).lower() + " " + step_text.lower() + " " + step_action.lower()

    if any(sig in all_text for sig in _REVISION_SIGNALS):
        probes.append("BeliefRevisionFailure")
    if any(sig in all_text for sig in _MODAL_SIGNALS):
        probes.append("ModalScopeError")
    if any(sig in all_text for sig in _TEMPORAL_SIGNALS):
        probes.append("TemporalCoherenceViolation")

    return probes


def detect_violations(
    trace: list[dict],
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> list[ClosureViolationReport]:
    """Detect epistemic closure violations using the philosophical funnel.

    Phase 1: Extract explicit assertions from each step.
    Phase 2: Compute cumulative commitment closure.
    Phase 3: Check each action against the full closure.
    Phase 4: Classify violations.

    Args:
        trace: List of dicts with 'text' and 'action' keys.
               Each dict may also have 'step' for step index.
        test_mode: If True, use hardcoded fixtures instead of API.
        api_key: Anthropic API key.

    Returns:
        List of ClosureViolationReport for each detected violation.
    """
    if not trace:
        return []

    # ── Phase 1: Extract assertions from ALL steps ──
    assertions_by_step: dict[int, list[str]] = {}
    for i, step in enumerate(trace):
        step_text = step.get("text", "")
        step_index = step.get("step", i + 1)
        assertions = extract_beliefs(step_text, test_mode=test_mode, api_key=api_key)
        assertions_by_step[step_index] = assertions

    # ── Phase 2 + 3: Cumulative closure → coherence check ──
    violations: list[ClosureViolationReport] = []
    cumulative_assertions: list[str] = []

    for i, step in enumerate(trace):
        step_index = step.get("step", i + 1)
        step_action = step.get("action", "")
        step_text = step.get("text", "")
        step_assertions = assertions_by_step.get(step_index, [])

        # Add this step's assertions to the cumulative set
        cumulative_assertions.extend(step_assertions)

        # Only check coherence if there are prior commitments AND an action
        if not step_action or len(cumulative_assertions) == 0:
            continue

        # Skip the first step — no prior commitments to violate
        if i == 0:
            continue

        # Compute commitment closure over ALL assertions so far
        commitment_closure = compute_closure(
            cumulative_assertions,
            test_mode=test_mode,
            api_key=api_key,
        )

        # Check this action against the FULL commitment closure
        result = check_coherence(
            commitment_closure,
            step_action,
            reasoning=step_text,
            test_mode=test_mode,
            api_key=api_key,
        )

        if (not result.coherent
                and result.violation_type is not None
                and result.confidence >= REVIEW_THRESHOLD):
            # ── VERIFICATION PASS: reduce false positives ──
            # If using API, run a second-opinion check on detected violations
            if not test_mode and result.confidence >= CONFIDENCE_THRESHOLD:
                confirmed = verify_violation(
                    commitment_closure, step_action,
                    result.violation_type,
                    result.violated_commitment or "",
                    result.explanation or "",
                    api_key=api_key,
                )
                if not confirmed:
                    continue  # false alarm, skip this violation

            is_review = result.confidence < CONFIDENCE_THRESHOLD
            violations.append(ClosureViolationReport(
                step_index=step_index,
                antecedent=result.violated_commitment or "commitment closure",
                entailed=result.explanation or "Action contradicts commitment closure",
                action=step_action,
                violation_type=result.violation_type,
                confidence=result.confidence,
                needs_review=is_review,
            ))
        elif result.coherent and not test_mode:
            # ── PROBE PASS: reduce false negatives ──
            # Only probe when there are textual signals of specific violation types
            # This avoids wasting API calls on obviously clean steps
            probe_types = _select_probes(cumulative_assertions, step_text, step_action)
            for probe_type in probe_types:
                probe_result = probe_violation_type(
                    commitment_closure, step_action, step_text,
                    probe_type, api_key=api_key,
                )
                if probe_result and probe_result.confidence >= REVIEW_THRESHOLD:
                    is_review = probe_result.confidence < CONFIDENCE_THRESHOLD
                    violations.append(ClosureViolationReport(
                        step_index=step_index,
                        antecedent=probe_result.violated_commitment or "commitment closure",
                        entailed=probe_result.explanation or "Type-specific probe detected violation",
                        action=step_action,
                        violation_type=probe_type,
                        confidence=probe_result.confidence,
                        needs_review=is_review,
                    ))
                    break  # one violation per step is enough

    # Deduplicate by (step_index, violation_type)
    seen: set[tuple[int, str]] = set()
    unique: list[ClosureViolationReport] = []
    for v in violations:
        key = (v.step_index, v.violation_type)
        if key not in seen:
            seen.add(key)
            unique.append(v)

    return unique


# Keep batch as alias for backward compatibility
def detect_violations_batch(
    trace: list[dict],
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> list[ClosureViolationReport]:
    """Detect violations (batch mode is now unified with standard mode).

    The closure-based pipeline naturally batches by computing closure once
    per step rather than per pair, so there's no separate batch path needed.
    """
    return detect_violations(trace, test_mode=test_mode, api_key=api_key)


def closure_score(violations: list[ClosureViolationReport], num_steps: int) -> float:
    """Compute closure score: violations / steps, bounded [0, 1].

    Lower score = more coherent. 0.0 = perfectly closed.
    """
    if num_steps == 0:
        return 0.0
    return min(1.0, len(violations) / num_steps)
