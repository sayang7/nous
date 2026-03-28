"""Aggregate metrics for closure violation analysis.

Computes summary statistics from a list of detected violations.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from nous.detector import ClosureViolationReport


@dataclass
class ClosureMetrics:
    """Aggregate metrics for closure violation detection."""
    closure_score: float  # Primary metric, [0,1], lower = more coherent
    violation_count: int
    violation_breakdown: dict[str, int]  # Count by ViolationType
    steps_analyzed: int
    most_common_violation: str  # Most frequent ViolationType or "None"


def compute_metrics(
    violations: list[ClosureViolationReport],
    num_steps: int,
) -> ClosureMetrics:
    """Compute aggregate metrics from a list of violations.

    Args:
        violations: List of detected ClosureViolationReport.
        num_steps: Total number of steps in the trace.

    Returns:
        ClosureMetrics with summary statistics.
    """
    if num_steps == 0:
        return ClosureMetrics(
            closure_score=0.0,
            violation_count=0,
            violation_breakdown={},
            steps_analyzed=0,
            most_common_violation="None",
        )

    breakdown = Counter(v.violation_type for v in violations)
    most_common = breakdown.most_common(1)[0][0] if breakdown else "None"

    return ClosureMetrics(
        closure_score=min(1.0, len(violations) / num_steps),
        violation_count=len(violations),
        violation_breakdown=dict(breakdown),
        steps_analyzed=num_steps,
        most_common_violation=most_common,
    )
