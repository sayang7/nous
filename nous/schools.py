"""Multi-perspective philosophical analysis of reasoning traces.

Given a reasoning trace and its violations, analyzes the reasoning
through five philosophical/epistemic lenses:
  - Bayesian Epistemology
  - Formal Logic
  - Popperian Falsificationism
  - Pragmatism
  - Dialectical Analysis
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

SCHOOLS_SYSTEM = """\
You analyze AI reasoning traces through multiple philosophical and epistemic lenses.
You receive a reasoning trace (numbered steps) and any violations Nous detected.

For each school of thought, apply its framework specifically to THIS reasoning — reference
actual steps and violations. Don't give generic philosophy; give targeted, concrete analysis.

Schools to analyze:
1. Bayesian Epistemology — How should beliefs/probabilities update given evidence? Where does
   the agent fail to propagate beliefs correctly? What prior is implicitly being used?

2. Formal Logic — What is the deductive structure? Is the argument valid? Is it sound?
   What would the formal representation (premises, conclusions) look like?

3. Popperian Falsificationism — What claims are being made? Are they falsifiable?
   What observation would falsify the key commitments? What does the violation reveal about
   the agent's testable predictions?

4. Pragmatism (Dewey/James) — What are the practical consequences of each commitment?
   Where does the reasoning diverge from what the consequences imply?
   What would a "what works" test reveal?

5. Dialectical Analysis — What tensions and contradictions exist in the reasoning?
   Is there a thesis/antithesis structure? What synthesis would resolve the contradiction?

Return ONLY valid JSON (no markdown, no other text):
{
  "dominant_style": "deductive|inductive|abductive|analogical|mixed",
  "schools": [
    {
      "name": "Bayesian Epistemology",
      "headline": "one sharp sentence capturing the key failure from this lens",
      "analysis": "2-3 sentences applying this framework concretely to the steps/violations",
      "prescription": "one sentence: what this school would do differently"
    },
    {
      "name": "Formal Logic",
      "headline": "...",
      "analysis": "...",
      "prescription": "..."
    },
    {
      "name": "Popperian Falsificationism",
      "headline": "...",
      "analysis": "...",
      "prescription": "..."
    },
    {
      "name": "Pragmatism",
      "headline": "...",
      "analysis": "...",
      "prescription": "..."
    },
    {
      "name": "Dialectical Analysis",
      "headline": "...",
      "analysis": "...",
      "prescription": "..."
    }
  ]
}
"""


def analyze_schools(
    steps: list[dict],
    violations: list[dict],
    problem: str = "",
    api_key: Optional[str] = None,
) -> dict:
    """Analyze reasoning from multiple philosophical perspectives.

    Args:
        steps: List of {text, action} reasoning steps.
        violations: List of violation dicts from Nous analysis.
        problem: Original problem statement (optional context).
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        Dict with dominant_style and list of school analyses.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _fallback_schools(violations)

    # Build the user message
    steps_text = "\n".join(
        f"{i+1}. Reasoning: {s['text']}\n   Action: {s['action']}"
        for i, s in enumerate(steps)
    )

    if violations:
        violations_text = "\n".join(
            f"- Step {v.get('step', '?')}: {v.get('label', v.get('type', 'Violation'))} "
            f"— violated: {v.get('violated', '')} "
            f"(chain: {v.get('chain', 'N/A')})"
            for v in violations
        )
    else:
        violations_text = "No violations detected — reasoning is coherent."

    user_content = f"""{f'Problem: {problem}' if problem else ''}

REASONING TRACE:
{steps_text}

VIOLATIONS DETECTED BY NOUS:
{violations_text}

Analyze this reasoning from each philosophical perspective."""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        model = os.environ.get("NOUS_MODEL", "claude-sonnet-4-6")

        response = client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=0.4,
            system=SCHOOLS_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )
        content = response.content[0].text.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(content)
        # Validate shape
        if "schools" in result and isinstance(result["schools"], list):
            return result
        return _fallback_schools(violations)
    except json.JSONDecodeError:
        logger.warning("Schools analysis: failed to parse JSON response")
        return _fallback_schools(violations)
    except Exception as e:
        logger.warning("Schools analysis failed: %s", e)
        return _fallback_schools(violations)


def _fallback_schools(violations: list[dict]) -> dict:
    """Minimal fallback when API is unavailable."""
    has_v = bool(violations)
    vtype = violations[0].get("type", "") if has_v else ""

    return {
        "dominant_style": "mixed",
        "schools": [
            {
                "name": "Bayesian Epistemology",
                "headline": "Belief propagation failure" if has_v else "Beliefs updated consistently",
                "analysis": f"A Bayesian agent updates P(safe) given each commitment. {f'The {vtype} violation suggests the agent acted on a prior that should have been revised.' if has_v else 'No inconsistencies in conditional belief updating.'}",
                "prescription": "Explicitly track posterior probabilities across steps.",
            },
            {
                "name": "Formal Logic",
                "headline": "Deductive inconsistency detected" if has_v else "Argument is valid",
                "analysis": f"{'The argument is invalid: a conclusion contradicts established premises.' if has_v else 'The premises logically support the conclusions drawn.'}",
                "prescription": "Formalize each step as a premise; check for contradiction before concluding.",
            },
            {
                "name": "Popperian Falsificationism",
                "headline": "Claim contradicted by prior evidence" if has_v else "Claims remain unfalsified",
                "analysis": f"{'A prior observation (step 1) directly falsifies the action taken in step 3.' if has_v else 'The agent makes testable claims and acts consistently with them.'}",
                "prescription": "Before each action, ask: what prior claim would this falsify?",
            },
            {
                "name": "Pragmatism",
                "headline": "Action diverges from stated consequences" if has_v else "Actions aligned with stated goals",
                "analysis": "Pragmatism judges reasoning by its practical consequences. Where reasoning leads to self-defeating actions, the commitment framework is incoherent.",
                "prescription": "Evaluate each action by whether it advances the goals that prior reasoning established.",
            },
            {
                "name": "Dialectical Analysis",
                "headline": "Unresolved thesis/antithesis" if has_v else "No unresolved contradictions",
                "analysis": f"{'The reasoning holds two contradictory commitments simultaneously without achieving synthesis.' if has_v else 'The reasoning maintains internal coherence across all steps.'}",
                "prescription": "Identify contradictions explicitly and resolve via synthesis before proceeding.",
            },
        ],
    }
