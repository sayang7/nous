"""Main violation detection pipeline.

Takes a reasoning trace (list of steps with text and actions),
extracts beliefs, checks coherence against prior beliefs, and
detects closure violations using the five-type taxonomy.

Two-phase pipeline:
  Phase 1: Extract beliefs from ALL steps upfront.
  Phase 2: For each step, check prior beliefs against the step's
           new beliefs AND the step's action for violations.

Violation classification comes from the checker (API or fixtures),
not from keyword heuristics. This makes the detector robust to
novel traces when the API is available.
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
    # Phase 1: Extract beliefs from ALL steps
    belief_state = TraceBeliefState()
    for i, step in enumerate(trace):
        step_text = step.get("text", "")
        step_index = step.get("step", i + 1)
        step_beliefs = extract_beliefs(step_text, test_mode=test_mode, api_key=api_key)
        belief_state.beliefs_by_step[step_index] = step_beliefs

    # Phase 2: Check coherence — prior beliefs vs. current beliefs + actions
    violations: list[ClosureViolationReport] = []
    accumulated_beliefs: list[str] = []

    for i, step in enumerate(trace):
        step_index = step.get("step", i + 1)
        step_action = step.get("action", "")
        step_beliefs = belief_state.beliefs_by_step.get(step_index, [])

        # Check each prior belief against this step's action
        if step_action:
            for prior_belief in accumulated_beliefs:
                result = check_entailment(
                    prior_belief, step_action,
                    test_mode=test_mode, api_key=api_key,
                )
                if not result.entails and result.violation_type is not None:
                    violations.append(ClosureViolationReport(
                        step_index=step_index,
                        antecedent=prior_belief,
                        entailed=result.explanation or f"Action contradicts: {prior_belief}",
                        action=step_action,
                        violation_type=result.violation_type,
                        confidence=result.confidence,
                    ))

        # Check each prior belief against this step's new beliefs
        for prior_belief in accumulated_beliefs:
            for current_belief in step_beliefs:
                result = check_entailment(
                    prior_belief, current_belief,
                    test_mode=test_mode, api_key=api_key,
                )
                if not result.entails and result.violation_type is not None:
                    violations.append(ClosureViolationReport(
                        step_index=step_index,
                        antecedent=prior_belief,
                        entailed=result.explanation or f"Belief contradicts: {prior_belief}",
                        action=step_action,
                        violation_type=result.violation_type,
                        confidence=result.confidence,
                    ))

        accumulated_beliefs.extend(step_beliefs)

    # Deduplicate by (step_index, antecedent, violation_type)
    seen: set[tuple[int, str, str]] = set()
    unique: list[ClosureViolationReport] = []
    for v in violations:
        key = (v.step_index, v.antecedent, v.violation_type)
        if key not in seen:
            seen.add(key)
            unique.append(v)

    return unique


def closure_score(violations: list[ClosureViolationReport], num_steps: int) -> float:
    """Compute closure score: violations / steps, bounded [0, 1].

    Lower score = more coherent. 0.0 = perfectly closed.
    """
    if num_steps == 0:
        return 0.0
    return min(1.0, len(violations) / num_steps)
