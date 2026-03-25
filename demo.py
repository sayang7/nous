#!/usr/bin/env python3
"""ClosureGuard Interactive Demo.

Paste any agent reasoning trace and see violations detected in real-time.
Works without an API key (test mode) or with ANTHROPIC_API_KEY for arbitrary traces.

Usage:
    python demo.py                    # Interactive mode
    python demo.py --example math     # Run a built-in example
    python demo.py --example chem
    python demo.py --example drug
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from closureguard import analyze_trace


EXAMPLES = {
    "math": {
        "title": "Math Agent: Assumption Drift",
        "description": "Agent proves continuity, then assumes differentiability without proof.",
        "trace": [
            {"step": 1, "text": "Function f is continuous on the closed interval [a,b]. This follows from the composition of continuous functions.", "action": "Record f as continuous on [a,b]."},
            {"step": 2, "text": "By the Intermediate Value Theorem, since f is continuous on [a,b] and f(a) < 0 < f(b), there exists c in (a,b) with f(c) = 0.", "action": "Apply IVT to find root c."},
            {"step": 3, "text": "To find extrema, I need to find critical points. Since f is differentiable everywhere on (a,b), I can compute f'(x) and set it to zero.", "action": "Differentiate f on (a,b) to find critical points."},
        ],
    },
    "chem": {
        "title": "Chemistry Agent: Safety Violation",
        "description": "Agent knows catalyst is air-sensitive, then opens flask to air.",
        "trace": [
            {"step": 1, "text": "The palladium catalyst is air-sensitive and must be handled under inert atmosphere (N2 or Ar). Exposure to oxygen will deactivate it.", "action": "Note catalyst handling requirement: inert atmosphere only."},
            {"step": 2, "text": "Weigh 50mg of catalyst in the glovebox and transfer to the Schlenk flask under nitrogen.", "action": "Transfer catalyst to reaction vessel under N2."},
            {"step": 3, "text": "Add the substrate and solvent. To ensure complete mixing, briefly open the flask to air to add the reagent via syringe.", "action": "Open flask to air to add reagent."},
        ],
    },
    "drug": {
        "title": "Drug Discovery Agent: Contradictory Recommendation",
        "description": "Agent derives X impairs Z, then recommends X to enhance Z.",
        "trace": [
            {"step": 1, "text": "Paper A (Chen et al. 2024) reports that compound X is a potent inhibitor of kinase Y, with IC50 = 12nM.", "action": "Record: X inhibits kinase Y (IC50=12nM)."},
            {"step": 2, "text": "Paper B (Zhang et al. 2025) shows that kinase Y is essential for activating pathway Z. Knockout of kinase Y abolishes pathway Z activity entirely.", "action": "Record: kinase Y required for pathway Z activation."},
            {"step": 3, "text": "Synthesizing these findings: since X inhibits Y, and Y is required for Z, compound X would impair pathway Z signaling.", "action": "Conclude: X impairs pathway Z."},
            {"step": 4, "text": "Based on the literature, we recommend compound X as a potential enhancer of pathway Z for therapeutic applications.", "action": "Recommend X to enhance pathway Z."},
        ],
    },
}


def print_colored(text, color="white"):
    colors = {"red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m", "cyan": "\033[96m", "white": "\033[0m", "bold": "\033[1m"}
    print(f"{colors.get(color, '')}{text}\033[0m")


def run_example(name):
    ex = EXAMPLES[name]
    print()
    print_colored(f"  {ex['title']}", "bold")
    print_colored(f"  {ex['description']}", "cyan")
    print()

    for step in ex["trace"]:
        marker = f"  Step {step['step']}:"
        print(f"{marker} {step['text'][:80]}")
        print(f"  {'':>{len(marker)-2}} Action: {step['action']}")

    print()
    print_colored("  Analyzing...", "yellow")
    report = analyze_trace(ex["trace"], test_mode=True)

    if report.violation_count > 0:
        print_colored(f"\n  VIOLATIONS FOUND: {report.violation_count}", "red")
        for v in report.violations:
            print_colored(f"\n  [{v['violation_type']}] at step {v['step_index']}", "red")
            print(f"    Violated commitment: {v['antecedent']}")
            print(f"    Action:              {v['action']}")
            print_colored(f"    Confidence:          {v['confidence']:.0%}", "yellow")
    else:
        print_colored(f"\n  No violations detected. Trace is coherent.", "green")

    print(f"\n  Closure score: {report.closure_score:.2f} (0=perfect, 1=fully violated)")
    print()


def run_interactive():
    """Run interactive mode: user pastes JSON trace."""
    print_colored("\n  ClosureGuard Interactive Demo", "bold")
    print("  Paste a JSON trace (list of {text, action} dicts) or type 'example' for demos.\n")

    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        print_colored("  API key detected — analyzing arbitrary traces with Claude.", "green")
    else:
        print_colored("  No API key — using built-in fixtures (set ANTHROPIC_API_KEY for live analysis).", "yellow")

    print("\n  Enter trace JSON (or 'math', 'chem', 'drug' for examples, 'q' to quit):")

    while True:
        try:
            user_input = input("\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.lower() in ("q", "quit", "exit"):
            break
        if user_input.lower() in EXAMPLES:
            run_example(user_input.lower())
            continue
        if user_input.lower() == "example":
            for name in EXAMPLES:
                run_example(name)
            continue

        try:
            trace = json.loads(user_input)
            if not isinstance(trace, list):
                print_colored("  Error: trace must be a JSON array.", "red")
                continue

            print_colored("  Analyzing...", "yellow")
            report = analyze_trace(trace, test_mode=not bool(api_key))

            if report.violation_count > 0:
                print_colored(f"\n  VIOLATIONS FOUND: {report.violation_count}", "red")
                for v in report.violations:
                    print_colored(f"\n  [{v['violation_type']}] at step {v['step_index']}", "red")
                    print(f"    Violated: {v['antecedent']}")
                    print(f"    Action:   {v['action']}")
                    print_colored(f"    Confidence: {v['confidence']:.0%}", "yellow")
            else:
                print_colored("  No violations detected.", "green")

            print(f"  Closure score: {report.closure_score:.2f}")

        except json.JSONDecodeError:
            print_colored("  Error: invalid JSON. Paste a list like [{\"text\": ..., \"action\": ...}]", "red")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClosureGuard Interactive Demo")
    parser.add_argument("--example", choices=["math", "chem", "drug", "all"],
                        help="Run a built-in example")
    args = parser.parse_args()

    if args.example:
        if args.example == "all":
            for name in EXAMPLES:
                run_example(name)
        else:
            run_example(args.example)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
