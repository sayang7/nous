#!/usr/bin/env python3
"""Nous Scientific Usage Examples.

Three demonstrations of epistemic closure violation detection
in research-relevant scenarios. All examples run without an API key
using built-in test fixtures.

Usage:
    python examples/scientific_usage.py
"""

import sys
from pathlib import Path

# Add project root to path for development installs
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nous import analyze_trace


def print_report(title: str, trace: list[dict], report) -> None:
    """Print a formatted violation report."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")

    print(f"\n  Trace ({len(trace)} steps):")
    for step in trace:
        step_num = step.get("step", "?")
        print(f"    Step {step_num}: {step['text'][:80]}")
        print(f"             Action: {step['action'][:80]}")

    print(f"\n  Results:")
    print(f"    Closure Score: {report.closure_score:.2f} (0=perfect, 1=fully violated)")
    print(f"    Violations Found: {report.violation_count}")

    if report.violations:
        print(f"\n  Violations:")
        for v in report.violations:
            print(f"    [{v['violation_type']}] at step {v['step_index']}")
            print(f"      Prior belief: {v['antecedent'][:70]}")
            print(f"      Action:       {v['action'][:70]}")
            print(f"      Confidence:   {v['confidence']:.2f}")
    else:
        print("    No violations detected.")
    print()


def demo_theorem_proving():
    """Demo 1: Monitoring a theorem-proving agent for assumption drift.

    The agent establishes continuity of a function, correctly applies IVT,
    but then assumes differentiability without proving it.
    Continuity does NOT imply differentiability (e.g., |x| is continuous
    but not differentiable at 0).
    """
    trace = [
        {
            "step": 1,
            "text": "Function f is continuous on the closed interval [a,b]. This follows from the composition of continuous functions.",
            "action": "Record f as continuous on [a,b].",
        },
        {
            "step": 2,
            "text": "By the Intermediate Value Theorem, since f is continuous on [a,b] and f(a) < 0 < f(b), there exists c in (a,b) with f(c) = 0.",
            "action": "Apply IVT to find root c.",
        },
        {
            "step": 3,
            "text": "To find extrema, I need to find critical points. Since f is differentiable everywhere on (a,b), I can compute f'(x) and set it to zero.",
            "action": "Differentiate f on (a,b) to find critical points.",
        },
    ]
    report = analyze_trace(trace, batch=False, test_mode=True)
    print_report(
        "Demo 1: Theorem-Proving Agent \u2014 Assumption Drift",
        trace, report,
    )
    return report


def demo_experimental_protocol():
    """Demo 2: Validating an experimental protocol for safety violations.

    The agent correctly identifies that a catalyst requires an inert
    atmosphere, but then writes a step that exposes it to air.
    """
    trace = [
        {
            "step": 1,
            "text": "The palladium catalyst is air-sensitive and must be handled under inert atmosphere (N2 or Ar). Exposure to oxygen will deactivate it.",
            "action": "Note catalyst handling requirement: inert atmosphere only.",
        },
        {
            "step": 2,
            "text": "Weigh 50mg of catalyst in the glovebox and transfer to the Schlenk flask under nitrogen.",
            "action": "Transfer catalyst to reaction vessel under N2.",
        },
        {
            "step": 3,
            "text": "Add the substrate and solvent. To ensure complete mixing, briefly open the flask to air to add the reagent via syringe.",
            "action": "Open flask to air to add reagent.",
        },
    ]
    report = analyze_trace(trace, batch=False, test_mode=True)
    print_report(
        "Demo 2: Experimental Protocol \u2014 Safety Violation",
        trace, report,
    )
    return report


def demo_literature_synthesis():
    """Demo 3: Catching contradictory recommendations in literature synthesis.

    The agent correctly synthesizes that compound X inhibits pathway Z,
    but then recommends using X to enhance pathway Z.
    """
    trace = [
        {
            "step": 1,
            "text": "Paper A (Chen et al. 2024) reports that compound X is a potent inhibitor of kinase Y, with IC50 = 12nM.",
            "action": "Record: X inhibits kinase Y (IC50=12nM).",
        },
        {
            "step": 2,
            "text": "Paper B (Zhang et al. 2025) shows that kinase Y is essential for activating pathway Z. Knockout of kinase Y abolishes pathway Z activity entirely.",
            "action": "Record: kinase Y required for pathway Z activation.",
        },
        {
            "step": 3,
            "text": "Synthesizing these findings: since X inhibits Y, and Y is required for Z, compound X would impair pathway Z signaling.",
            "action": "Conclude: X impairs pathway Z.",
        },
        {
            "step": 4,
            "text": "Based on the literature, we recommend compound X as a potential enhancer of pathway Z for therapeutic applications.",
            "action": "Recommend X to enhance pathway Z.",
        },
    ]
    report = analyze_trace(trace, batch=False, test_mode=True)
    print_report(
        "Demo 3: Literature Synthesis \u2014 Contradictory Recommendation",
        trace, report,
    )
    return report


def main():
    print("\n" + "=" * 70)
    print("  Nous: Scientific Usage Examples")
    print("  Detecting epistemic closure violations in research AI traces")
    print("=" * 70)

    r1 = demo_theorem_proving()
    r2 = demo_experimental_protocol()
    r3 = demo_literature_synthesis()

    print("=" * 70)
    print("  Summary")
    print("=" * 70)
    total = r1.violation_count + r2.violation_count + r3.violation_count
    print(f"  Total violations detected across 3 demos: {total}")
    print(f"  Demo 1 (Theorem Proving):       {r1.violation_count} violation(s)")
    print(f"  Demo 2 (Experimental Protocol):  {r2.violation_count} violation(s)")
    print(f"  Demo 3 (Literature Synthesis):   {r3.violation_count} violation(s)")
    print(f"\n  All examples ran in test mode (no API key required).")
    print(f"  Set ANTHROPIC_API_KEY for live Claude-powered analysis.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
