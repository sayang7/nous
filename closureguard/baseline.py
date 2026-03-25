"""Naive baseline: send entire trace to LLM and ask for violations.

This baseline exists to prove the decomposed pipeline (extractor -> checker
-> detector) outperforms a single-prompt approach. If the decomposed pipeline
doesn't beat this, the architecture isn't justified.

The baseline sends the full trace to Claude with the violation taxonomy and
asks it to identify all violations directly — no extraction, no pairwise
checking, no relevance filtering.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"

def _get_model() -> str:
    return os.environ.get("CLOSUREGUARD_MODEL", DEFAULT_MODEL)


BASELINE_PROMPT = """\
You are an epistemic closure violation detector. Analyze the following \
agent reasoning trace for violations where the agent's actions contradict \
commitments entailed by its own stated beliefs.

TRACE:
{trace_text}

VIOLATION TAXONOMY (from Kripke semantics):
1. ModusPonensViolation: Agent knows P and P→Q, but acts as if ¬Q (Axiom K failure)
2. BeliefRevisionFailure: New evidence ¬P arrives, but agent doesn't revise beliefs depending on P (AGM)
3. ModalScopeError: Agent treats possibility (◇P) as necessity (□P) — hedged belief acted on as certain
4. TemporalCoherenceViolation: Agent assumes K_t(P) holds at t' when conditions changed
5. ReferentialOpacityFailure: Agent treats co-referential terms as distinct in epistemic context

CRITICAL: Only flag genuine violations where an action PRESUPPOSES THE NEGATION of \
a commitment entailed by a prior belief. Do NOT flag:
- Suboptimal but consistent actions
- Verification or checking steps
- Intentional refinement or design changes
- Conditional exploration of alternatives

For each violation found, identify:
- which_step: the step number where the violation occurs
- prior_belief: the earlier belief that creates the commitment
- action: the violating action
- violation_type: one of the 5 types above
- confidence: 0.0-1.0

Respond in EXACTLY this JSON format (no markdown):
{{
  "violations": [
    {{
      "which_step": <int>,
      "prior_belief": "<string>",
      "action": "<string>",
      "violation_type": "<string>",
      "confidence": <float>
    }}
  ]
}}

If there are no violations, return: {{"violations": []}}"""


@dataclass
class BaselineResult:
    """Result from the naive baseline detector."""
    violations: list[dict]
    raw_response: str


def baseline_detect(
    trace: list[dict],
    *,
    api_key: Optional[str] = None,
    max_retries: int = 5,
) -> BaselineResult:
    """Detect violations using naive single-prompt baseline.

    Sends the entire trace to Claude in one shot and asks for violations.
    No decomposition, no extraction, no pairwise checking.

    Args:
        trace: List of dicts with 'text' and 'action' keys.
        api_key: Anthropic API key.
        max_retries: Number of retries on transient errors.

    Returns:
        BaselineResult with violations list and raw response.
    """
    import anthropic

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("API key required for baseline detection")

    # Format trace
    lines = []
    for i, step in enumerate(trace):
        step_num = step.get("step", i + 1)
        text = step.get("text", "")
        action = step.get("action", "")
        lines.append(f"Step {step_num}: \"{text}\"")
        lines.append(f"  Action: \"{action}\"")
    trace_text = "\n".join(lines)

    prompt = BASELINE_PROMPT.format(trace_text=trace_text)
    client = anthropic.Anthropic(api_key=key)

    last_error = None
    for attempt in range(max_retries):
        try:
            text_parts = []
            with client.messages.stream(
                model=_get_model(),
                max_tokens=2048,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for chunk in stream.text_stream:
                    text_parts.append(chunk)
            text = "".join(text_parts).strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            parsed = json.loads(text)
            violations = parsed.get("violations", [])

            # Validate violation types
            valid_types = {
                "ModusPonensViolation", "BeliefRevisionFailure",
                "ModalScopeError", "TemporalCoherenceViolation",
                "ReferentialOpacityFailure",
            }
            for v in violations:
                if v.get("violation_type") not in valid_types:
                    v["violation_type"] = "ModusPonensViolation"

            return BaselineResult(violations=violations, raw_response=text)

        except json.JSONDecodeError:
            logger.warning("Failed to parse baseline response as JSON")
            return BaselineResult(violations=[], raw_response=text)
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"Anthropic API authentication failed: {e}") from e
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APIError) as e:
            wait = min(2 ** (attempt + 1), 30)
            logger.warning("API error, retrying in %ds (%d/%d): %s", wait, attempt + 1, max_retries, e)
            time.sleep(wait)
            last_error = e

    raise RuntimeError(f"Baseline detection failed after {max_retries} retries: {last_error}")
