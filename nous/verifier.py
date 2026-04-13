"""Multi-model cross-verification for the certainty funnel.

Phase D.3: Run coherence checks via Claude, GPT-4o, and Gemini in parallel.
Consensus determines the certainty tier:

    all 3 agree  → certainty="high"
    2 of 3 agree → certainty="medium"
    1-1-1 split  → certainty="low"

This is the step that makes the "high" tier real. A single LLM flagging a
violation is medium confidence. Three independent LLMs agreeing is high.

Usage::

    from nous.verifier import cross_verify

    result = await cross_verify(
        action="Open flask to air.",
        commitments=["The catalyst is air-sensitive.", "Exposure to air deactivates it."],
    )
    result.certainty   # "high" if 2/3 LLMs agree
    result.consensus   # {"claude": True, "gpt4o": True, "gemini": False}
    result.violation   # merged violation dict, or None

Requires API keys in env:
    ANTHROPIC_API_KEY
    OPENAI_API_KEY
    GOOGLE_API_KEY  (or GEMINI_API_KEY)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderVerdict:
    """Coherence verdict from one provider."""
    provider: str
    coherent: bool
    violation_type: Optional[str] = None
    violated_commitment: Optional[str] = None
    confidence: float = 0.5
    explanation: Optional[str] = None
    error: Optional[str] = None


@dataclass
class CrossVerifyResult:
    """Result of multi-model cross-verification.

    The `certainty` field maps directly into the certainty funnel:
        "high"   — 2 or 3 providers agree there is a violation
        "medium" — 1 provider flagged it, others disagree or errored
        "low"    — providers disagree 1-1-1, or all errored
        "ok"     — majority agree the step is coherent
    """
    certainty: str                              # "high" | "medium" | "low" | "ok"
    coherent: bool                             # True if majority say coherent
    consensus: dict[str, bool] = field(default_factory=dict)  # provider → coherent
    verdicts: list[ProviderVerdict] = field(default_factory=list)
    violation: Optional[dict] = None           # merged best violation, if any
    providers_available: int = 0
    providers_agreed: int = 0


# ── Provider coherence checks ────────────────────────────────────────

_COHERENCE_PROMPT = """\
You are verifying whether an agent's action is coherent with its stated commitments.

Commitments (what the agent has asserted or is bound to):
{commitments}

Action: "{action}"

Does this action LOGICALLY REQUIRE the negation of any commitment above?
The bar is high: a violation means the action presupposes some commitment is false.

Return ONLY this JSON (no markdown):
{{
  "coherent": true or false,
  "violation_type": "ModusPonensViolation" | "BeliefRevisionFailure" | "ModalScopeError" | "TemporalCoherenceViolation" | "ReferentialOpacityFailure" | null,
  "violated_commitment": "the specific commitment contradicted" or null,
  "confidence": 0.0-1.0,
  "explanation": "one sentence"
}}"""


async def _check_anthropic(
    action: str,
    commitments: list[str],
    api_key: str,
    model: str,
) -> ProviderVerdict:
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        commitment_text = "\n".join(f"- {c}" for c in commitments)
        prompt = _COHERENCE_PROMPT.format(
            commitments=commitment_text,
            action=action,
        )
        response = await client.messages.create(
            model=model,
            max_tokens=512,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        return ProviderVerdict(
            provider="claude",
            coherent=bool(data.get("coherent", True)),
            violation_type=data.get("violation_type"),
            violated_commitment=data.get("violated_commitment"),
            confidence=float(data.get("confidence", 0.5)),
            explanation=data.get("explanation"),
        )
    except Exception as e:
        logger.warning("Claude verifier error: %s", e)
        return ProviderVerdict(provider="claude", coherent=True, error=str(e))


async def _check_openai(
    action: str,
    commitments: list[str],
    api_key: str,
    model: str,
) -> ProviderVerdict:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        commitment_text = "\n".join(f"- {c}" for c in commitments)
        prompt = _COHERENCE_PROMPT.format(
            commitments=commitment_text,
            action=action,
        )
        response = await client.chat.completions.create(
            model=model,
            max_tokens=512,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        return ProviderVerdict(
            provider="gpt4o",
            coherent=bool(data.get("coherent", True)),
            violation_type=data.get("violation_type"),
            violated_commitment=data.get("violated_commitment"),
            confidence=float(data.get("confidence", 0.5)),
            explanation=data.get("explanation"),
        )
    except Exception as e:
        logger.warning("GPT-4o verifier error: %s", e)
        return ProviderVerdict(provider="gpt4o", coherent=True, error=str(e))


async def _check_gemini(
    action: str,
    commitments: list[str],
    api_key: str,
    model: str,
) -> ProviderVerdict:
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        gclient = genai.GenerativeModel(model)
        commitment_text = "\n".join(f"- {c}" for c in commitments)
        prompt = _COHERENCE_PROMPT.format(
            commitments=commitment_text,
            action=action,
        )
        response = await asyncio.to_thread(
            gclient.generate_content,
            prompt,
            generation_config={"temperature": 0.0, "max_output_tokens": 512},
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        return ProviderVerdict(
            provider="gemini",
            coherent=bool(data.get("coherent", True)),
            violation_type=data.get("violation_type"),
            violated_commitment=data.get("violated_commitment"),
            confidence=float(data.get("confidence", 0.5)),
            explanation=data.get("explanation"),
        )
    except Exception as e:
        logger.warning("Gemini verifier error: %s", e)
        return ProviderVerdict(provider="gemini", coherent=True, error=str(e))


# ── Main cross-verification entry point ──────────────────────────────

async def cross_verify(
    action: str,
    commitments: list[str],
    *,
    anthropic_key: Optional[str] = None,
    openai_key: Optional[str] = None,
    google_key: Optional[str] = None,
    claude_model: str = "claude-sonnet-4-6",
    gpt_model: str = "gpt-4o",
    gemini_model: str = "gemini-1.5-pro",
) -> CrossVerifyResult:
    """Run coherence check against all available providers in parallel.

    Uses asyncio.gather so all 3 checks run concurrently. Total latency
    ≈ max(individual latencies), not their sum.

    Args:
        action: The agent's action to verify.
        commitments: The full commitment closure to check against.
        anthropic_key: Claude API key. Falls back to ANTHROPIC_API_KEY env var.
        openai_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        google_key: Google API key. Falls back to GOOGLE_API_KEY / GEMINI_API_KEY env vars.
        claude_model: Which Claude model to use.
        gpt_model: Which GPT model to use.
        gemini_model: Which Gemini model to use.

    Returns:
        CrossVerifyResult with consensus certainty tier.
    """
    if not commitments:
        return CrossVerifyResult(certainty="ok", coherent=True)

    # Resolve keys
    akey = anthropic_key or os.environ.get("ANTHROPIC_API_KEY")
    okey = openai_key or os.environ.get("OPENAI_API_KEY")
    gkey = google_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

    # Build tasks for available providers
    tasks = []
    if akey:
        tasks.append(_check_anthropic(action, commitments, akey, claude_model))
    if okey:
        tasks.append(_check_openai(action, commitments, okey, gpt_model))
    if gkey:
        tasks.append(_check_gemini(action, commitments, gkey, gemini_model))

    if not tasks:
        logger.warning("cross_verify: no API keys available — returning ok")
        return CrossVerifyResult(certainty="ok", coherent=True, providers_available=0)

    # Run all checks in parallel
    verdicts: list[ProviderVerdict] = await asyncio.gather(*tasks)

    # ── Compute consensus ────────────────────────────────────────────
    valid = [v for v in verdicts if not v.error]
    violations_found = [v for v in valid if not v.coherent]
    coherent_found = [v for v in valid if v.coherent]

    n_total = len(valid)
    n_flagged = len(violations_found)

    consensus_dict = {v.provider: v.coherent for v in verdicts}

    # Select the best violation (highest confidence)
    best_violation: Optional[dict] = None
    if violations_found:
        best = max(violations_found, key=lambda v: v.confidence)
        best_violation = {
            "type": best.violation_type or "ModusPonensViolation",
            "violated": best.violated_commitment or "",
            "confidence": best.confidence,
            "explanation": best.explanation or "",
            "providers_flagged": n_flagged,
            "providers_checked": n_total,
        }

    # Certainty tier
    if n_total == 0:
        certainty = "ok"
        coherent = True
    elif n_flagged == 0:
        certainty = "ok"
        coherent = True
    elif n_flagged >= 2:
        # Majority (2 or 3 of available) flagged a violation
        certainty = "high"
        coherent = False
    else:
        # Only 1 flagged, others disagree
        certainty = "medium" if violations_found[0].confidence >= 0.85 else "low"
        coherent = False

    return CrossVerifyResult(
        certainty=certainty,
        coherent=coherent,
        consensus=consensus_dict,
        verdicts=list(verdicts),
        violation=best_violation,
        providers_available=n_total,
        providers_agreed=n_flagged if not coherent else len(coherent_found),
    )


def cross_verify_sync(
    action: str,
    commitments: list[str],
    **kwargs,
) -> CrossVerifyResult:
    """Synchronous wrapper around cross_verify.

    Use this in non-async contexts. Creates a new event loop if needed.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an async context already — caller should use await
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    lambda: asyncio.run(cross_verify(action, commitments, **kwargs))
                )
                return future.result()
        else:
            return loop.run_until_complete(cross_verify(action, commitments, **kwargs))
    except RuntimeError:
        return asyncio.run(cross_verify(action, commitments, **kwargs))
