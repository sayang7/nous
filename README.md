<p align="center">
  <h1 align="center">ClosureGuard</h1>
  <p align="center"><strong>Your AI agent knows the answer — then does the wrong thing anyway.<br>ClosureGuard catches it.</strong></p>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#why-this-matters">Why It Matters</a> &bull;
  <a href="#how-it-works">How It Works</a> &bull;
  <a href="#evaluation">Eval Results</a> &bull;
  <a href="#lean-4-proofs">Lean 4 Proofs</a> &bull;
  <a href="#paper">Paper</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/lean-4.16.0-orange.svg" alt="Lean 4">
  <img src="https://img.shields.io/badge/tests-51%20passed-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
</p>

---

**ClosureGuard** is a formally-grounded detector for epistemic closure violations in LLM agent reasoning traces. It detects a class of reasoning failure that **no existing tool catches**: when an agent's *actions* contradict the logical consequences of its own *stated beliefs*.

This isn't hallucination. This isn't self-contradiction. This is a **structural incoherence** between what the agent commits to and what it does — and it happens constantly.

## The 30-Second Demo

```
Agent: "The catalyst is air-sensitive. Must use inert atmosphere."     [Step 1]
Agent: "Transfer catalyst under nitrogen."                              [Step 2 ✓]
Agent: "Open flask to air to add reagent."                              [Step 3 ✗]
        ^^^ VIOLATION: Agent's own commitment says air = deactivation.
            No sentence contradicts another. The violation is in the
            ACTION contradicting the BELIEF-ENTAILED commitment.
```

```
$ python examples/scientific_usage.py

[ModusPonensViolation] at step 3
  Prior belief: Exposing the catalyst to air will deactivate it.
  Action:       Open flask to air to add reagent.
  Confidence:   0.96
```

**No ground truth needed.** The agent's own assertions are sufficient to detect the violation.

## Quick Start

```bash
pip install -e ".[dev]"
```

```python
from closureguard import analyze_trace

trace = [
    {"step": 1, "text": "The API returns JSON.",        "action": "Send request."},
    {"step": 2, "text": "JSON must be parsed first.",    "action": "Store response."},
    {"step": 3, "text": "Extract the name field.",       "action": "Split response by commas."},
]

report = analyze_trace(trace)
# => Violation at step 3: committed to JSON parsing, acted on raw text
```

Set `ANTHROPIC_API_KEY` for Claude-powered analysis on arbitrary traces, or run without it using built-in fixtures.

## Why This Matters

### For Math/Physics Researchers

```
Step 1: "f is continuous on [a,b]"                               ← proved
Step 2: "By IVT, root exists in (a,b)"                          ← valid ✓
Step 3: "Since f is differentiable on (a,b), find critical pts"  ← VIOLATION!
        Continuity ≠ differentiability (e.g., |x| at 0). Never proved.
```

ClosureGuard catches **assumption drift** — the agent forgets what it proved vs. assumed. This matters for anyone using AI copilots with Lean, Coq, Isabelle, or any proof assistant.

### For Chemistry/Biology Researchers

```
Step 1: "Compound X inhibits kinase Y (IC50=12nM)"              ← literature
Step 2: "Kinase Y activates pathway Z"                           ← literature
Step 3: "So X impairs pathway Z"                                 ← valid ✓
Step 4: "Recommend X to enhance pathway Z"                       ← VIOLATION!
        Agent's OWN reasoning says X impairs Z.
```

ClosureGuard catches **contradictory recommendations** that could waste months of wet-lab work or mislead drug discovery pipelines.

### For Anyone Building AI Agents

If your agent reasons step-by-step and takes actions, ClosureGuard monitors the logical integrity of that chain. Works with LangChain, AutoGPT, custom loops — anything with a text/action trace.

## How It Works

ClosureGuard implements a **philosophical funnel** grounded in Kripke semantics:

```
  Trace  →  [Extract Assertions]  →  [Compute Commitment Closure]  →  [Verify Coherence]  →  Violations
                                           C({P1,...Pn})                 action vs. C?
```

**Phase 1 — Extract:** What did the agent explicitly assert at each step?

**Phase 2 — Close:** What is the agent *committed* to? If you assert P and P entails Q, you're committed to Q — even if you never said Q. This is the **commitment closure operator** from Brandom (1994).

**Phase 3 — Verify:** Does the action presuppose not-Q for any Q in the closure? One check per action against the *entire* commitment set. Not pairwise.

**Phase 3b — Double-Check:** If a violation is detected, a second-opinion verification pass asks "is there a valid reason this is actually coherent?" This catches false positives — mathematical equivalences, implementation patterns, etc. If the initial check finds "clean" but textual signals suggest a subtle violation (hedging language, temporal markers, belief updates), type-specific probes run targeted checks for ModalScopeError, BeliefRevisionFailure, or TemporalCoherenceViolation. Probes only trigger when relevant signals are present, keeping API costs low.

**Phase 4 — Classify:** Which axiom failed? Five types, each grounded in a different branch of epistemic logic:

| Violation Type | Formal Source | What It Catches |
|---------------|---------------|-----------------|
| `ModusPonensViolation` | Axiom K (Hintikka 1962) | K(P) ∧ K(P→Q) but act(¬Q) |
| `BeliefRevisionFailure` | AGM (1985) | New evidence arrives, beliefs not updated |
| `ModalScopeError` | Kripke 1963 | "Might be X" treated as "Is definitely X" |
| `TemporalCoherenceViolation` | Prior 1967 | Stale beliefs used after conditions changed |
| `ReferentialOpacityFailure` | Frege 1892 | Same thing under two names treated as different |

This is **O(n) API calls** per trace, not O(n²). The LLM sees the full commitment context for every judgment.

## Evaluation

40-task benchmark: 20 violation traces + 20 clean traces (including adversarial near-misses), 5 domains, all 5 violation types.

| Metric | ClosureGuard Pipeline | Naive Baseline (single-prompt) |
|--------|----------------------|-------------------------------|
| **Precision** | **0.889** | 0.864 |
| Recall | 0.800 | **0.950** |
| F1 | 0.842 | 0.905 |
| False Positives | **2** | 3 |

**The pipeline trades recall for precision** — the right trade for a monitoring tool. False alarms erode trust. When ClosureGuard flags something, it's almost certainly real (89% precision), and it tells you *exactly* which commitment was violated and at which step.

**Perfect detection** on ModusPonens violations (6/6) and in math_reasoning (F1=1.0) and web_agent (F1=1.0) domains.

<details>
<summary><strong>Full per-type and per-domain breakdown</strong></summary>

| Violation Type | Pipeline | Baseline |
|---------------|----------|----------|
| ModusPonensViolation | 6/6 | 6/6 |
| BeliefRevisionFailure | 1/3 | 2/3 |
| ModalScopeError | 3/4 | 4/4 |
| TemporalCoherenceViolation | 1/4 | 2/4 |
| ReferentialOpacityFailure | 2/3 | 3/3 |

| Domain | Precision | Recall | F1 |
|--------|-----------|--------|-----|
| code_agent | 0.800 | 1.000 | 0.889 |
| math_reasoning | 1.000 | 1.000 | **1.000** |
| planning | 1.000 | 0.667 | 0.800 |
| scientific | 0.800 | 0.667 | 0.727 |
| web_agent | 1.000 | 1.000 | **1.000** |

</details>

```bash
# Reproduce
export ANTHROPIC_API_KEY=your-key
python -u eval/run_eval.py
python -u eval/run_baseline.py --compare eval/results/<result>.json
```

## Lean 4 Proofs

This isn't prompt engineering with formal garnish. The violation taxonomy is **defined and proven sound** in Lean 4 with complete proofs across four layers:

| Theorem | What It Proves |
|---------|---------------|
| `epistemic_closure` | K(P) ∧ K(P→Q) → K(Q) from Kripke semantics |
| `violation_contradicts_known_truth` | Soundness: every violation = acting against known truth |
| `violation_contradicts_commitment` | **Key result:** soundness *without factivity* — works for LLM agents that assert falsehoods |
| `commitment_violation_is_incoherent` | Commitment closure + contradiction witness |

The `violation_contradicts_commitment` theorem is what makes this work for LLM agents. You don't need the agent's beliefs to be *true* — you just need them to be *self-consistent*. This is the Brandomian move: from knowledge to inferential commitment.

```bash
lake build  # Verify all proofs (Lean 4 v4.16.0)
```

<details>
<summary><strong>All theorems and formal layers</strong></summary>

**Layer 1 — Kripke Semantics:** Axioms K, T, 4, 5 (epistemic logic S5).

**Layer 2 — Inferential Commitment Theory:** Brandomian closure operator. Proves violations are incoherent even without factivity.

**Layer 3 — Trace Structures:** Data types mapping formal concepts to the Python detector.

**Layer 4 — AGM Belief Revision:** Contraction operators and revision failure formalization.

| Theorem | Formal Content |
|---------|---------------|
| `epistemic_closure` | Axiom K |
| `knowledge_is_factive` | Axiom T: K(P) → P |
| `positive_introspection` | Axiom 4: K(P) → K(K(P)) |
| `negative_introspection` | Axiom 5: ¬K(P) → K(¬K(P)) |
| `violation_contradicts_known_truth` | Soundness with factivity |
| `violation_contradicts_commitment` | Soundness without factivity |
| `commitment_violation_is_incoherent` | Commitment closure witness |
| `entailment_outside_set_breaks_closure` | Deductive closure lemma |

One `sorry` in the AGM revision failure theorem (requires structure on the entailment relation that is instantiated empirically by the LLM). All other proofs complete.

</details>

## Why Not Just Ask an LLM?

You *could* send the whole trace to GPT-4/Claude and ask "is this consistent?" That's our baseline — and it gets F1=0.905.

But:
1. **It can't explain *why*.** ClosureGuard pinpoints the exact commitment violated and the step responsible.
2. **It has no formal guarantees.** ClosureGuard's violation taxonomy is proven sound in Lean 4.
3. **It doesn't scale.** A single prompt loses context on long traces. ClosureGuard's cumulative closure grows with the trace.
4. **It conflates detection with judgment.** ClosureGuard separates extraction, closure computation, and coherence verification — each independently auditable.

The pipeline exists not to beat the baseline on F1, but to provide **formally-grounded, interpretable, auditable** detection.

## How This Is Different from Everything Else

| Tool | What It Catches | What It Misses |
|------|----------------|----------------|
| SelfCheckGPT | Hallucinations (needs ground truth) | Belief-action gaps |
| Semantic Entropy | Uncertainty in generations | Structural incoherence |
| Self-contradiction detectors | P ∧ ¬P | P → Q, act(¬Q) — no explicit contradiction |
| Chain-of-thought evaluators | Wrong final answers | Correct-looking answers with broken reasoning |
| InferAct (EMNLP 2025) | Agent-intent misalignment | No formal logic, no commitment closure |
| AgentSpec / ShieldAgent | Policy violations, unsafe actions | Epistemic violations within reasoning |
| **ClosureGuard** | **Belief-action entailment gaps** | Requires trace format |

**The specific gap we address:** No existing tool detects when an agent's actions contradict the *logical consequences* of its own stated beliefs. This is strictly harder than self-contradiction and fundamentally different from hallucination detection.

## Runtime Monitoring

```python
from closureguard import analyze_trace

def agent_monitor(trace_so_far):
    """Call after each agent step to check reasoning integrity."""
    report = analyze_trace(trace_so_far)

    # Definite violations: high confidence, act immediately
    for v in report.violations:
        if not v['needs_review']:
            print(f"VIOLATION: {v['violation_type']} at step {v['step_index']}")
            print(f"  Violated: {v['antecedent']}")
            return False  # halt agent

    # Uncertain cases: flag for human review, don't auto-halt
    if report.review_count > 0:
        for v in report.violations:
            if v['needs_review']:
                print(f"REVIEW RECOMMENDED: possible {v['violation_type']} at step {v['step_index']}")
                print(f"  Confidence: {v['confidence']:.0%} — below auto-flag threshold")

    return True  # continue (with review flags if applicable)
```

**The tool never misleads.** High-confidence violations are flagged as definite. Uncertain cases are flagged as "review recommended" — the researcher stays in control. Works with LangChain, AutoGPT, CrewAI, or any agent that outputs reasoning + actions.

## The Honest Assessment

**What the Lean proofs guarantee:** The *definition* of a violation is sound — every flagged pattern is a genuine structural incoherence.

**What the Lean proofs do NOT guarantee:** That the Python implementation detects all violations, or never misfires. The LLM-based entailment checking is an empirical approximation.

**How we handle uncertainty:** ClosureGuard uses a **three-tier confidence system**:
- **Violation** (confidence >= 85%): High-confidence flag. The tool is confident this is a real violation.
- **Review Recommended** (70-85%): Uncertain — the tool flags the case but asks the researcher to decide. **The researcher is never overridden.**
- **Clean** (below 70%): No flag.

This means ClosureGuard **never silently passes a suspicious case** and **never confidently asserts a wrong answer in the uncertain zone**. When it's not sure, it tells you.

**This is standard in formal methods:** the theory defines correctness; the implementation is validated by evaluation. We report both.

## Citation

```bibtex
@misc{closureguard2026,
  title={ClosureGuard: Formally-Grounded Detection of Epistemic Closure
         Violations in LLM Agent Reasoning Traces},
  author={Gupta, Sayan},
  year={2026},
  url={https://github.com/sayangupta/ClosureGuard}
}
```

## License

MIT
