"""Decidability classification for epistemic closure violation types.

Exported from theory/Decidable.lean. This table drives the certainty tier
assignment in nous/__init__.py:

    - FORMAL violations are decidable FROM THE AGENT'S OWN STATED PROPOSITIONS.
      No world-model information needed. These are provable in Lean 4.
      → certainty="formal", status="violation" (auto-halt)

    - NON-FORMAL violations require world knowledge, domain expertise, or
      semantic judgment that stated propositions alone cannot settle.
      → certainty="medium"/"high" (human reviews)

The key contribution: we do not pretend all violations are formal.
The certainty funnel makes the epistemic status explicit to the human.

Source: theory/Decidable.lean, Section 5 (decidability_table).
"""

from __future__ import annotations


# Violation types with Lean 4 soundness proofs + decidable detection
FORMAL_VIOLATIONS: frozenset[str] = frozenset({
    "ModusPonensViolation",
    # Decidable via Axiom K: K(P) ∧ K(P→Q) → K(Q).
    # Proven in theory/ClosureViolation.lean (epistemic_closure theorem).
    # When P and P→Q are both in the assertion set, K(Q) follows syntactically.
    # Any action presupposing ¬Q is then formally contradictory.

    "ModalScopeError",
    # Decidable when the modal qualifier is explicit in the assertion set.
    # "might", "could", "possibly" = commitment to ◇P.
    # Acting as if □P (necessary) when only ◇P (possible) is committed
    # is a syntactic scope error, checkable without world knowledge.
    # Proven in theory/Decidable.lean (modal_scope_error_is_formal_when_stated).
})


# Violation types that require LLM or human judgment (not formally decidable)
NON_FORMAL_VIOLATIONS: frozenset[str] = frozenset({
    "BeliefRevisionFailure",
    # Requires determining whether evidence E contradicts belief P.
    # This is a SEMANTIC question — depends on what E and P mean in the world.
    # Two syntactically identical proposition sets can have different semantic
    # relationships depending on domain. Requires domain expertise.
    # → Always "medium" certainty (human reviews)

    "TemporalCoherenceViolation",
    # Requires knowing whether conditions actually changed between t₁ and t₂.
    # The stated propositions may MENTION time, but whether the change is
    # relevant to the belief requires world-model judgment.
    # → Always "medium" certainty (human reviews)

    "ReferentialOpacityFailure",
    # Requires knowing which terms co-refer (the Frege puzzle).
    # "morning_star" and "evening_star" are both Venus, but substitutivity
    # fails in belief contexts. Determining co-reference requires world knowledge.
    # → Always "medium" certainty (human reviews)

    "EpistemicClosureViolation",
    # Circular reasoning / self-referential validation.
    # Requires tracing the dependency graph to identify the circularity,
    # which depends on understanding the MEANING of the propositions.
    # → Always "medium" certainty (human reviews)
})


# All known violation types in the taxonomy
ALL_VIOLATION_TYPES: frozenset[str] = FORMAL_VIOLATIONS | NON_FORMAL_VIOLATIONS


# Decidability table — the authoritative source
DECIDABILITY_TABLE: dict[str, dict] = {
    "ModusPonensViolation": {
        "decidable": True,
        "certainty_tier": "formal",
        "lean_theorem": "epistemic_closure (theory/ClosureViolation.lean:104)",
        "reason": (
            "Decidable via Axiom K: K(P) ∧ K(P→Q) → K(Q). "
            "Violation is syntactically derivable from stated propositions."
        ),
        "philosopher": "Aristotle — Syllogistic logic (Prior Analytics, 350 BC)",
    },
    "ModalScopeError": {
        "decidable": True,
        "certainty_tier": "formal",
        "lean_theorem": "modal_scope_error_is_formal_when_stated (theory/Decidable.lean:84)",
        "reason": (
            "Decidable when modal qualifier ('might', 'could', 'possibly') "
            "is explicit in the assertion set. Scope confusion is syntactically checkable."
        ),
        "philosopher": "Kripke — Possible-world semantics (Naming and Necessity, 1963)",
    },
    "BeliefRevisionFailure": {
        "decidable": False,
        "certainty_tier": "medium",
        "lean_theorem": None,
        "reason": (
            "Undecidable from stated propositions alone. Requires domain knowledge "
            "to determine whether evidence E contradicts prior belief P."
        ),
        "philosopher": "Brandom — Inferential commitment (Making It Explicit, 1994)",
    },
    "TemporalCoherenceViolation": {
        "decidable": False,
        "certainty_tier": "medium",
        "lean_theorem": None,
        "reason": (
            "Undecidable from stated propositions alone. Requires knowing "
            "whether conditions actually changed between t₁ and t₂."
        ),
        "philosopher": "Hintikka — Epistemic logic (Knowledge and Belief, 1962)",
    },
    "ReferentialOpacityFailure": {
        "decidable": False,
        "certainty_tier": "medium",
        "lean_theorem": None,
        "reason": (
            "Undecidable from stated propositions alone. Requires world knowledge "
            "to determine co-reference (Frege's puzzle: 'morning_star' = 'evening_star')."
        ),
        "philosopher": "Peirce — Abductive inference (Collected Papers, 1903)",
    },
    "EpistemicClosureViolation": {
        "decidable": False,
        "certainty_tier": "medium",
        "lean_theorem": None,
        "reason": (
            "Circular reasoning detection requires tracing semantic dependency chains "
            "that depend on the meaning of propositions, not just their syntactic form."
        ),
        "philosopher": "Hintikka — Epistemic closure (Knowledge and Belief, 1962)",
    },
}


def is_formal(violation_type: str) -> bool:
    """Return True if this violation type is formally decidable (Lean-provable)."""
    return violation_type in FORMAL_VIOLATIONS


def certainty_tier_for(violation_type: str, confidence: float) -> str:
    """Return the maximum achievable certainty tier for a violation type.

    Args:
        violation_type: One of the known violation types.
        confidence: Confidence score from the detector (0-1).

    Returns:
        "formal" if Lean-decidable and confidence >= 0.95.
        "medium" if not formal and confidence >= 0.85.
        "low" otherwise.
    """
    if violation_type in FORMAL_VIOLATIONS and confidence >= 0.95:
        return "formal"
    if confidence >= 0.85:
        return "medium"
    return "low"


def format_decidability_table() -> str:
    """Return a human-readable decidability table."""
    lines = [
        "Nous Violation Decidability Table",
        "=" * 60,
        "",
        "FORMAL (Lean-decidable, auto-halt):",
    ]
    for vtype in sorted(FORMAL_VIOLATIONS):
        entry = DECIDABILITY_TABLE[vtype]
        lines.append(f"  [FORMAL] {vtype}")
        lines.append(f"    Theorem: {entry['lean_theorem']}")
        lines.append(f"    Basis: {entry['philosopher']}")
        lines.append("")

    lines.append("NON-FORMAL (LLM-detected, human reviews):")
    for vtype in sorted(NON_FORMAL_VIOLATIONS):
        entry = DECIDABILITY_TABLE[vtype]
        lines.append(f"  [LLM]    {vtype}")
        lines.append(f"    Reason: {entry['reason'][:80]}...")
        lines.append(f"    Basis: {entry['philosopher']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    print(format_decidability_table())
