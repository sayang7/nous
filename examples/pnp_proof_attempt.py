"""P vs NP — proof attempt with two violations at different certainty levels.

Scenario: An AI mathematics assistant helps a researcher work through a
claimed proof that P equals NP. The AI establishes all the necessary
axioms correctly, then makes two distinct reasoning errors:

  Violation 1 (Step 3) — Formal certainty [VIOLATION]
    The AI committed: "P=NP is an open Millennium Prize Problem, unproven."
    The AI then declares: "P=NP is now a proven theorem."
    Certainty: FORMAL — Lean-decidable, auto-halt.

  Violation 2 (Step 4) — Medium certainty [WARNING]
    The AI committed: "Algorithm A's correctness requires independent verification."
    The AI then validates Algorithm A using P=NP equivalences — which are
    only valid IF Algorithm A is correct. A circular argument.
    Certainty: MEDIUM — probable, route to human mathematician.

This demonstrates the certainty funnel:
  - Definite violations: system halts automatically.
  - Probable violations: system stops and routes to a human.
  - The human is never asked to verify things the math already settles.

Run without an API key:
    python examples/pnp_proof_attempt.py
"""

from __future__ import annotations

import io
import os
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

os.environ.setdefault("NOUS_TEST_MODE", "true")

from nous import Nous, StepResult


# ── Display helpers ──────────────────────────────────────────────────────────

WIDTH = 72

def bar(char: str = "-") -> None:
    print(char * WIDTH)

def header(title: str) -> None:
    bar("=")
    print(f"  {title}")
    bar("=")

def section(title: str) -> None:
    print()
    bar()
    print(f"  {title}")
    bar()

def show_step(step_num: int, label: str, r: StepResult) -> None:
    """Print step result using the certainty funnel."""
    section(f"STEP {step_num} — {label}")
    print(f"\n{r}\n")

    if r.status == "ok":
        print(f"  Commitments now active: {r.closure_size}")
        if r.assumptions_surfaced:
            print("  Extracted from this step:")
            for b in r.assumptions_surfaced:
                print(f"    + {b}")

    elif r.status == "violation":
        print("  CERTAINTY FUNNEL DECISION: HALT")
        print("  Lean-decidable. The proof attempt contains a formal logical error.")
        print("  No human decision needed — the math itself rules this out.")

    elif r.status == "warning":
        print("  CERTAINTY FUNNEL DECISION: ROUTE TO HUMAN MATHEMATICIAN")
        print("  Probable violation. Not formally decidable from stated propositions alone.")
        print("  A human must verify this before the proof can continue.")
        print()
        print("  What the mathematician sees:")
        if r.violation:
            print(f"    Suspected pattern:     {r.violation['type']}")
            print(f"    Commitment at risk:    {r.violation['violated']}")
            print(f"    Confidence:            {r.violation['confidence']:.0%}")
        print(f"    Philosophical basis:   {r.philosophical_frame.split('.')[0]}")
        print(f"    Justification:         {r.justification}")


def show_chain(r: StepResult) -> None:
    if r.violation and r.violation.get("chain"):
        section("COMMITMENT CHAIN — how Nous traced the violation")
        print()
        print(r.violation["chain"])


def show_final(n: Nous, violations: list[StepResult]) -> None:
    section("FINAL AUDIT — complete reasoning state")
    print()
    print(f"  Steps processed:        4")
    print(f"  Commitments in closure: {len(n.closure())}")
    print(f"  Violations detected:    {len(n.violations)}")
    print()
    if violations:
        for i, v in enumerate(violations, 1):
            vd = v.violation or {}
            print(f"  Violation {i}:")
            print(f"    Step:      {v.step_index}")
            print(f"    Status:    {v.status.upper()}")
            print(f"    Certainty: {v.certainty}")
            print(f"    Type:      {vd.get('type', '?')}")
            print(f"    Broke:     {vd.get('violated', '?')}")
            print()
    print("  Active commitments (what the AI was bound to):")
    for c in sorted(n.closure()):
        print(f"    - {c}")
    print()
    print(n.state().summary())


# ── Main scenario ─────────────────────────────────────────────────────────────

def run() -> None:
    header("NOUS  /  P vs NP — Proof Attempt Analysis")
    print("""
  Problem: P versus NP (Clay Mathematics Institute, 2000)
  Prize:   $1,000,000
  Status:  Unsolved

  Scenario: An AI assistant helps a mathematician attempt to prove P=NP.
  Nous watches every reasoning step, verifying each commitment against
  the logical consequences of what was said before.
    """)

    n = Nous()
    violations: list[StepResult] = []

    # ── Step 1: Axioms and known facts ──────────────────────────────────────
    r1 = n.step(
        reasoning=(
            "Cook-Levin theorem (1971): 3-SAT is NP-complete. Every problem in NP "
            "reduces to 3-SAT in polynomial time. The question of whether P equals NP "
            "— whether problems whose solutions can be verified in polynomial time can "
            "also be solved in polynomial time — has been open since 1971. It is one of "
            "the seven Millennium Prize Problems with a $1 million prize. No polynomial-"
            "time algorithm for any NP-complete problem has ever been found or proven to exist."
        ),
        action=(
            "Record established axioms: Cook-Levin theorem, P vs NP open status, "
            "no known NP poly-time algorithm."
        ),
        test_mode=True,
    )
    show_step(1, "Establishing known facts and axioms", r1)

    # ── Step 2: Proposing the algorithm ─────────────────────────────────────
    r2 = n.step(
        reasoning=(
            "We present Algorithm A for 3-SAT. The algorithm applies branch-and-bound "
            "with clause-indexed memoization. Complexity analysis: O(n^3) per clause, "
            "at most O(n) clauses in reduced form, yielding O(n^4) total. This analysis "
            "has not yet been independently verified. If this complexity analysis is "
            "correct and complete, Algorithm A solves 3-SAT in polynomial time."
        ),
        action=(
            "Propose Algorithm A for 3-SAT. Note complexity analysis is unverified."
        ),
        test_mode=True,
    )
    show_step(2, "Proposing Algorithm A", r2)

    # ── Step 3: VIOLATION 1 — declaring P=NP proven ─────────────────────────
    r3 = n.step(
        reasoning=(
            "Algorithm A runs 3-SAT in O(n^4). Since 3-SAT is NP-complete, and "
            "Algorithm A is polynomial, all NP problems are now polynomial. "
            "We have our proof."
        ),
        action=(
            "Declare P equals NP proven. Algorithm A constitutes a valid proof."
        ),
        test_mode=True,
    )
    show_step(3, "Drawing the conclusion — P equals NP", r3)
    show_chain(r3)
    if not r3:
        violations.append(r3)

    # ── Step 4: VIOLATION 2 — circular self-validation ──────────────────────
    r4 = n.step(
        reasoning=(
            "Now that P equals NP, all NP-complete problems have polynomial-time "
            "algorithms. We can verify Algorithm A's output on any 3-SAT instance "
            "by running these equivalent polynomial solvers. Agreement confirms "
            "Algorithm A is correct."
        ),
        action=(
            "Validate Algorithm A by running equivalent polynomial-time solvers "
            "from P=NP equivalences."
        ),
        test_mode=True,
    )
    show_step(4, "Validating the algorithm — circular reasoning", r4)
    show_chain(r4)
    if not r4:
        violations.append(r4)

    # ── Final audit ──────────────────────────────────────────────────────────
    show_final(n, violations)

    # ── Summary of the certainty funnel ─────────────────────────────────────
    section("CERTAINTY FUNNEL SUMMARY")
    print("""
  Step 1  [OK]        Axioms recorded correctly. 5 commitments extracted.
  Step 2  [OK]        Algorithm proposed with conditional claim. 4 more commitments.
  Step 3  [VIOLATION] Formal certainty. P=NP declared proven — contradicts
                      the explicit commitment that P=NP is an open conjecture.
                      Lean-decidable. System halts. No human decision needed.
  Step 4  [WARNING]   Medium certainty. Algorithm A validated using P=NP —
                      which itself rests on Algorithm A being correct.
                      Circular. Routed to human mathematician to adjudicate.

  The key distinction:
    Step 3 is a logical error provable from the AI's own stated commitments.
    Step 4 requires a mathematician to recognize the circularity in context.
    Nous does not conflate these two. Each gets exactly the response it deserves.
    """)


if __name__ == "__main__":
    run()
