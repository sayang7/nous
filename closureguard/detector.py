"""Main violation detection pipeline.

Takes a reasoning trace (list of steps with text and actions),
extracts beliefs, checks entailments, and detects closure violations
matching the five-type taxonomy from the Lean formalization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from closureguard.extractor import extract_beliefs
from closureguard.checker import check_entailment, EntailmentResult


# Violation types — must match Lean taxonomy exactly
VIOLATION_TYPES = [
    "ModusPonensViolation",
    "BeliefRevisionFailure",
    "ModalScopeError",
    "TemporalCoherenceViolation",
    "ReferentialOpacityFailure",
]


@dataclass
class ClosureViolationReport:
    """A detected closure violation in a reasoning trace."""
    step_index: int
    antecedent: str
    entailed: str
    action: str
    violation_type: str
    confidence: float


@dataclass
class TraceBeliefState:
    """Accumulated belief state across trace steps."""
    beliefs_by_step: dict[int, list[str]] = field(default_factory=dict)
    all_beliefs: list[str] = field(default_factory=list)


def detect_violations(
    trace: list[dict],
    *,
    test_mode: bool = False,
    api_key: Optional[str] = None,
) -> list[ClosureViolationReport]:
    """Detect epistemic closure violations in a reasoning trace.

    Args:
        trace: List of dicts with 'text' and 'action' keys.
               Each dict may also have 'step' for step index.
        test_mode: If True, use hardcoded fixtures instead of API.
        api_key: Anthropic API key.

    Returns:
        List of ClosureViolationReport for each detected violation.
    """
    violations: list[ClosureViolationReport] = []
    state = TraceBeliefState()

    for i, step in enumerate(trace):
        step_text = step.get("text", "")
        step_action = step.get("action", "")
        step_index = step.get("step", i + 1)

        # Extract beliefs from this step
        step_beliefs = extract_beliefs(step_text, test_mode=test_mode, api_key=api_key)
        state.beliefs_by_step[step_index] = step_beliefs

        # Check for violations: does the action in this step contradict
        # any belief entailed by prior beliefs?
        prior_beliefs = list(state.all_beliefs)  # snapshot before adding new
        state.all_beliefs.extend(step_beliefs)

        # Check belief-to-belief coherence
        for prior_belief in prior_beliefs:
            for current_belief in step_beliefs:
                violations.extend(
                    _check_belief_action_coherence(
                        prior_belief=prior_belief,
                        current_belief=current_belief,
                        action=step_action,
                        step_index=step_index,
                        test_mode=test_mode,
                        api_key=api_key,
                    )
                )

        # Check belief-to-action coherence: treat the action as an
        # implicit belief and check if it contradicts entailed beliefs.
        # This catches the belief-ACTION gap (the novel contribution).
        if step_action:
            action_as_belief = step_action
            for prior_belief in prior_beliefs:
                violations.extend(
                    _check_belief_action_coherence(
                        prior_belief=prior_belief,
                        current_belief=action_as_belief,
                        action=step_action,
                        step_index=step_index,
                        test_mode=test_mode,
                        api_key=api_key,
                    )
                )

    # Deduplicate violations by (step_index, antecedent, violation_type)
    seen: set[tuple[int, str, str]] = set()
    unique: list[ClosureViolationReport] = []
    for v in violations:
        key = (v.step_index, v.antecedent, v.violation_type)
        if key not in seen:
            seen.add(key)
            unique.append(v)

    return unique


def _check_belief_action_coherence(
    prior_belief: str,
    current_belief: str,
    action: str,
    step_index: int,
    test_mode: bool,
    api_key: Optional[str],
) -> list[ClosureViolationReport]:
    """Check if a prior belief and current belief/action are coherent.

    Detects violations by checking:
    1. Does the prior belief entail the current belief? If so, coherent.
    2. Does the prior belief entail something the action contradicts?
    3. Classify the violation type based on the belief pair structure.
    """
    violations: list[ClosureViolationReport] = []

    # Check if prior belief entails the current belief
    entailment = check_entailment(
        prior_belief, current_belief, test_mode=test_mode, api_key=api_key
    )

    # If prior entails current with low confidence, it may indicate
    # the current belief contradicts what the prior commits to
    if not entailment.entails and entailment.confidence < 0.3:
        # Check the reverse: does the prior belief entail something
        # that the current belief contradicts?
        violation_type = _classify_violation(
            prior_belief, current_belief, action, test_mode, api_key
        )
        if violation_type is not None:
            violations.append(
                ClosureViolationReport(
                    step_index=step_index,
                    antecedent=prior_belief,
                    entailed=_get_entailed_belief(prior_belief, current_belief),
                    action=action,
                    violation_type=violation_type,
                    confidence=1.0 - entailment.confidence,
                )
            )

    return violations


def _classify_violation(
    prior_belief: str,
    current_belief: str,
    action: str,
    test_mode: bool,
    api_key: Optional[str],
) -> Optional[str]:
    """Classify the type of closure violation, if any.

    Uses structural heuristics and entailment patterns to map
    violations to the five-type taxonomy.
    """
    prior_lower = prior_belief.lower()
    current_lower = current_belief.lower()

    # ModalScopeError: possible/necessary confusion (check before temporal
    # to avoid false matches on substrings like "at " in "that ")
    possibility_markers = ["possible", "might", "could", "may ", "perhaps"]
    necessity_markers = ["is ", "will ", "must ", "certainly", "definitely"]
    if (any(m in prior_lower for m in possibility_markers) and
            any(m in current_lower for m in necessity_markers)):
        return "ModalScopeError"

    # TemporalCoherenceViolation: time-indexed beliefs
    # Use word-boundary-aware patterns to avoid "at" in "that"
    import re
    temporal_patterns = [r"\bas of\b", r"\bat \d", r"\bsince \b", r"\bafter \b", r"\bbefore \b", r"\buntil \b"]
    if any(re.search(p, prior_lower) for p in temporal_patterns):
        return "TemporalCoherenceViolation"

    # BeliefRevisionFailure: prior states something no longer holds
    revision_markers = ["deleted", "removed", "no longer", "was ", "changed", "updated"]
    if any(m in prior_lower for m in revision_markers):
        return "BeliefRevisionFailure"

    # ReferentialOpacityFailure: co-referential terms treated as distinct
    if ("refers to" in prior_lower or "is the same as" in prior_lower):
        if "no information" in current_lower or "no existing" in current_lower:
            return "ReferentialOpacityFailure"

    # Default: ModusPonensViolation (most general category)
    # The prior belief entails Q, but the action/new belief acts as ¬Q
    return "ModusPonensViolation"


def _get_entailed_belief(prior_belief: str, contradicting_belief: str) -> str:
    """Infer what the prior belief entailed that was violated."""
    # The entailed belief is the negation of what the contradicting belief states
    return f"Negation of: {contradicting_belief}"


def closure_score(violations: list[ClosureViolationReport], num_steps: int) -> float:
    """Compute closure score: violations / steps, bounded [0, 1].

    Lower score = more coherent. 0.0 = perfectly closed.
    """
    if num_steps == 0:
        return 0.0
    return min(1.0, len(violations) / num_steps)
