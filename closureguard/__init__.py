"""ClosureGuard: Detecting Epistemic Closure Violations in LLM Agent Reasoning Traces."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__version__ = "0.1.0"


def _load_dotenv() -> None:
    """Load .env file from project root if it exists. No external dependency needed."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not os.environ.get(key):
                os.environ[key] = value


_load_dotenv()


@dataclass
class ClosureReport:
    """High-level analysis report from ClosureGuard."""

    closure_score: float
    violation_count: int
    violations: list[dict] = field(default_factory=list)
    violation_breakdown: dict[str, int] = field(default_factory=dict)
    steps_analyzed: int = 0
    review_count: int = 0  # violations in the "uncertain" band needing human review


def analyze_trace(
    trace: list[dict],
    *,
    batch: bool = True,  # kept for backward compatibility, no longer used
    test_mode: Optional[bool] = None,
    api_key: Optional[str] = None,
) -> ClosureReport:
    """Analyze an agent reasoning trace for epistemic closure violations.

    Implements the philosophical funnel from Kripke semantics:
        Assertions → Commitment Closure → Coherence Check → Classification

    Args:
        trace: List of dicts, each with 'text' (reasoning) and 'action' keys.
               Optional 'step' key for step index.
        test_mode: If True, use built-in fixtures (no API). If None, auto-detect.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        ClosureReport with violations, scores, and breakdown.

    Example:
        >>> from closureguard import analyze_trace
        >>> trace = [
        ...     {"text": "The API returns JSON.", "action": "Parse response."},
        ...     {"text": "Got the data.", "action": "Split by commas."},
        ... ]
        >>> report = analyze_trace(trace)
        >>> print(report.closure_score, report.violation_count)
    """
    from closureguard.detector import detect_violations, closure_score
    from closureguard.scorer import compute_metrics

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if test_mode is None:
        test_mode = not bool(key)

    violations = detect_violations(trace, test_mode=test_mode, api_key=key)

    metrics = compute_metrics(violations, len(trace))

    violation_dicts = [
        {
            "step_index": v.step_index,
            "antecedent": v.antecedent,
            "entailed": v.entailed,
            "action": v.action,
            "violation_type": v.violation_type,
            "confidence": v.confidence,
            "needs_review": v.needs_review,
        }
        for v in violations
    ]
    review_count = sum(1 for v in violations if v.needs_review)

    return ClosureReport(
        closure_score=metrics.closure_score,
        violation_count=metrics.violation_count,
        violations=violation_dicts,
        violation_breakdown=metrics.violation_breakdown,
        steps_analyzed=len(trace),
        review_count=review_count,
    )
