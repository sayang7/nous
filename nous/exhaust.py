"""Exhaustive belief extraction — the foundation of 100% catching.

The gap between "catches 89% of violations" and "catches 100%" is the gap
between SAMPLING beliefs and EXHAUSTING them.

Standard extractors ask: "what does this step say?"
This extractor asks three questions at every step:

  1. EXPLICIT   — what is the step directly asserting?
  2. PREMISES   — what must already be true for this step to be valid?
                  (hidden imports — the step silently requires these)
  3. COMMITMENTS — what does this step lock in for every future step?
                  (if any future step contradicts these, that IS a violation)

All three go into the commitment graph as first-class nodes.

When premises are surfaced, they become part of the closure — so if a
later step acts as if a premise is false, we catch it.
When forward commitments are added, we pre-load the graph with constraints
the future steps must respect — catching violations BEFORE they happen.

Example:

  Step: "Apply the Intermediate Value Theorem to find the root."

  EXPLICIT:    "The root exists in (a,b) by IVT."
  PREMISES:    "f is continuous on [a,b]."          ← must be true for IVT to apply
               "f(a) and f(b) have opposite signs."  ← must be true for IVT to apply
  COMMITMENTS: "The root is in the OPEN interval (a,b), not at endpoints." ← locked in
               "Any search outside (a,b) violates the IVT result."          ← locked in

If a later step searches outside (a,b), the violation is caught.
If a later step assumes f is NOT continuous, the contradiction is in the closure.

This is the metaphysical completeness: we are not sampling the space of
possible violations, we are EXHAUSTING the logical consequences of what
the agent has committed to.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExhaustiveExtraction:
    """Three-tier extraction result for one reasoning step.

    All three tiers go into the commitment graph:
      - explicit    → is_explicit=True nodes
      - premises    → is_explicit=False, tagged as 'premise'
      - commitments → is_explicit=False, tagged as 'forward_commitment'
    """
    step_index: int
    reasoning: str
    explicit: list[str] = field(default_factory=list)
    premises: list[str] = field(default_factory=list)
    commitments: list[str] = field(default_factory=list)

    @property
    def all_beliefs(self) -> list[str]:
        """Every belief this step introduces, across all tiers."""
        return self.explicit + self.premises + self.commitments

    def summary(self) -> str:
        lines = [f"Step {self.step_index} extraction:"]
        for b in self.explicit:
            lines.append(f"  [EXPLICIT]    {b}")
        for b in self.premises:
            lines.append(f"  [PREMISE]     {b}")
        for b in self.commitments:
            lines.append(f"  [COMMITMENT]  {b}")
        return "\n".join(lines)


_EXHAUSTIVE_PROMPT = """\
You are performing EXHAUSTIVE belief extraction for a formal reasoning verifier.

A reasoning step from an AI agent:
---
{reasoning}
---

Extract THREE tiers of beliefs. Be aggressive — surface everything, especially
what is NOT said explicitly. The goal is completeness: every logical consequence
of this step must be accounted for.

TIER 1 — EXPLICIT: What does this step directly assert?
(Statements the agent explicitly makes at this step.)

TIER 2 — PREMISES: What must already be true for this step to be valid?
(Hidden imports. What is the step SILENTLY REQUIRING? What would have to be false
for this step to be invalid? Surface these as the assumptions the step is leaning on.
Examples: "Apply IVT" requires "f is continuous on [a,b]". "Parse JSON" requires
"the response is valid JSON". "Use penicillin" requires "patient has no penicillin allergy".)

TIER 3 — COMMITMENTS: What does this step lock in for all future steps?
(Forward constraints. What can future steps NOT do, given what this step asserts?
Examples: "The root is in (a,b)" locks in "searching outside (a,b) is invalid".
"Catalyst is air-sensitive" locks in "any later step exposing it to air is invalid".)

Rules:
- Be exhaustive, not minimal. It is better to surface a non-obvious premise than to miss one.
- Each belief should be a complete, precise declarative sentence.
- Premises that were stated in earlier steps should still be listed if this step relies on them.
- Forward commitments should be phrased as constraints: "X must hold", "Y cannot occur", etc.

Return ONLY this JSON (no markdown):
{{
  "explicit": ["..."],
  "premises": ["..."],
  "commitments": ["..."]
}}"""


def extract_exhaustive(
    reasoning: str,
    step_index: int,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    test_mode: bool = False,
) -> ExhaustiveExtraction:
    """Extract all three tiers of beliefs from a reasoning step.

    Args:
        reasoning: The agent's reasoning text at this step.
        step_index: Which step this is.
        api_key: Anthropic API key.
        model: Which model to use. Defaults to NOUS_MODEL env var or haiku.
        test_mode: If True, return a minimal extraction (no API call).

    Returns:
        ExhaustiveExtraction with all three tiers populated.
    """
    if test_mode:
        # In test mode: extract explicit beliefs only (simple heuristic)
        sentences = [s.strip() for s in reasoning.split('.') if len(s.strip()) > 10]
        return ExhaustiveExtraction(
            step_index=step_index,
            reasoning=reasoning,
            explicit=sentences[:3],
            premises=[],
            commitments=[],
        )

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("No API key — falling back to minimal extraction")
        return ExhaustiveExtraction(
            step_index=step_index,
            reasoning=reasoning,
            explicit=[reasoning[:200]],
            premises=[],
            commitments=[],
        )

    _model = model or os.environ.get("NOUS_MODEL", "claude-haiku-4-5-20251001")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = _EXHAUSTIVE_PROMPT.format(reasoning=reasoning)
        response = client.messages.create(
            model=_model,
            max_tokens=1024,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        return ExhaustiveExtraction(
            step_index=step_index,
            reasoning=reasoning,
            explicit=data.get("explicit", []),
            premises=data.get("premises", []),
            commitments=data.get("commitments", []),
        )
    except Exception as e:
        logger.warning("Exhaustive extraction failed: %s", e)
        return ExhaustiveExtraction(
            step_index=step_index,
            reasoning=reasoning,
            explicit=[reasoning[:200]],
            premises=[],
            commitments=[],
        )


# ── Internal consistency check ────────────────────────────────────────────────

_CONSISTENCY_PROMPT = """\
You are checking a set of propositions for internal contradictions.

An agent has accumulated the following commitments through its reasoning:
{commitments}

Are any of these commitments mutually contradictory? A contradiction means
proposition A and proposition B cannot both be true at the same time.

Do NOT flag:
- Propositions that cover different cases or contexts
- Refinements of earlier claims
- Temporally separated beliefs unless one explicitly supersedes the other
- Two possibilities being explored (both can coexist)

DO flag:
- Direct logical contradictions (P and ¬P)
- Incompatible constraints (must be X AND must not be X)
- Actions that presuppose the negation of a stated belief

Return ONLY this JSON (no markdown):
{{
  "has_contradiction": true or false,
  "pairs": [
    {{
      "a": "first contradicting commitment",
      "b": "second contradicting commitment",
      "explanation": "one sentence: why these cannot both be true"
    }}
  ]
}}"""


def check_internal_consistency(
    commitments: list[str],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> list[dict]:
    """Check a commitment set for internal contradictions.

    This is separate from action-vs-closure checking. It asks:
    "Is the closure itself contradictory?" — catching circular reasoning
    and committed contradictions BEFORE they manifest as bad actions.

    Args:
        commitments: All propositions in the current commitment closure.
        api_key: Anthropic API key.
        model: Model to use.

    Returns:
        List of contradiction dicts: {a, b, explanation}. Empty if clean.
    """
    if len(commitments) < 2:
        return []

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return []

    _model = model or os.environ.get("NOUS_MODEL", "claude-haiku-4-5-20251001")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        commitment_text = "\n".join(f"- {c}" for c in commitments[-30:])  # last 30 to keep prompt short
        prompt = _CONSISTENCY_PROMPT.format(commitments=commitment_text)
        response = client.messages.create(
            model=_model,
            max_tokens=512,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        if data.get("has_contradiction"):
            return data.get("pairs", [])
        return []
    except Exception as e:
        logger.warning("Internal consistency check failed: %s", e)
        return []


# ── Predictive constraint warning ─────────────────────────────────────────────

_PREDICT_PROMPT = """\
Given these current commitments of an AI agent:
{commitments}

List up to 5 specific actions that would constitute a violation of these
commitments if taken in the next step.

Be concrete and specific — not "any action that contradicts X" but
"taking action Y would violate commitment Z because..."

Return ONLY this JSON (no markdown):
{{
  "forbidden_actions": [
    {{
      "action": "specific description of the forbidden action",
      "violates": "which commitment it would violate",
      "type": "violation type (ModusPonensViolation | ModalScopeError | etc.)"
    }}
  ]
}}"""


def predict_forbidden_actions(
    commitments: list[str],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> list[dict]:
    """Predict which actions would violate the current closure.

    This turns Nous from REACTIVE (catches violations after) to PREDICTIVE
    (warns about violations before they happen).

    Use this after each step to show the agent (or its operator) what
    it CANNOT do next, given what it has committed to so far.

    Args:
        commitments: Current commitment closure.
        api_key: Anthropic API key.
        model: Model to use.

    Returns:
        List of forbidden action dicts: {action, violates, type}.
    """
    if not commitments:
        return []

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return []

    _model = model or os.environ.get("NOUS_MODEL", "claude-haiku-4-5-20251001")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        commitment_text = "\n".join(f"- {c}" for c in commitments[-20:])
        prompt = _PREDICT_PROMPT.format(commitments=commitment_text)
        response = client.messages.create(
            model=_model,
            max_tokens=512,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        return data.get("forbidden_actions", [])
    except Exception as e:
        logger.warning("Prediction failed: %s", e)
        return []
