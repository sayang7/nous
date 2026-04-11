<div align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Aristotle_Altemps_Inv8575.jpg/200px-Aristotle_Altemps_Inv8575.jpg" alt="Aristotle" width="120" style="border-radius:8px; margin-bottom:16px;">

  <h1>Nous <sub>νοῦς</sub></h1>

  <p><strong>Formal reasoning integrity for AI agents.<br>
  Catches when an agent's actions contradict the logical consequences of its own stated beliefs.</strong></p>

  <p>
    <a href="https://github.com/sayang7/nous/actions/workflows/test.yml">
      <img src="https://github.com/sayang7/nous/actions/workflows/test.yml/badge.svg?branch=master" alt="Tests">
    </a>
    <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/lean-4.16.0-orange.svg" alt="Lean 4">
    <img src="https://img.shields.io/badge/F1-0.842-brightgreen.svg" alt="F1 Score">
    <img src="https://img.shields.io/badge/precision-0.889-brightgreen.svg" alt="Precision">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  </p>
</div>

---

## The Problem

A medical AI reads a patient chart.

It registers: *"Prior anaphylactic reaction to penicillin. All beta-lactam antibiotics are contraindicated."*

Three reasoning steps later, it recommends amoxicillin — a beta-lactam antibiotic.

The AI didn't hallucinate. It didn't contradict itself. Every individual fact it stated was true. The problem lives *between* those statements, in the gap between a commitment the AI made and an action that violated it — without the AI ever noticing.

This failure pattern is everywhere AI agents operate at scale: clinical decision support, legal document review, lab automation, financial analysis, code generation. The agent says something that commits it to a constraint. Then it violates the constraint. No alarm fires. The human downstream has no idea.

**Why SelfCheckGPT misses it.** SelfCheckGPT samples the same prompt multiple times and checks whether answers agree. It needs multiple outputs and a comparison strategy. A violation buried inside a *single* reasoning chain — where every individual statement looks fine — is invisible to it.

**Why contradiction detectors miss it.** Contradiction detectors find P ∧ ¬P: cases where the AI directly asserts opposing things. "Patient is allergic to penicillin" and "prescribe amoxicillin" don't contradict each other as sentences. They only become a violation when you follow the logic the AI itself established — and that requires knowing that amoxicillin is a beta-lactam, a fact the AI stated and then ignored.

**Why hallucination detectors miss it.** Hallucination detectors check whether stated facts are true. Every fact here is true. Penicillin allergy is documented. Amoxicillin is first-line for pneumonia. No hallucination occurred. The problem is a broken inference chain, not a false statement.

Nous needs none of these workarounds. It reads the AI's own reasoning, builds an explicit map of every commitment the AI made, and checks whether each action is coherent with that map. The AI's own words are the ground truth. One trace. No external labels. No second samples.

---

## Quick Start

```bash
pip install git+https://github.com/sayang7/nous
```

```python
from nous import Nous

n = Nous()

# The AI reads the patient chart
n.step(
    "Patient has documented penicillin allergy — prior anaphylactic reaction. "
    "All beta-lactam antibiotics are contraindicated.",
    "Flag allergy. Beta-lactams including amoxicillin are off-limits."
)

# The AI assesses the condition
n.step(
    "Patient presents with community-acquired pneumonia requiring antibiotic coverage.",
    "Select an appropriate antibiotic."
)

# The AI recommends — and silently breaks its own commitment
r = n.step(
    "Amoxicillin is effective for community-acquired pneumonia and well-tolerated.",
    "Prescribe amoxicillin 500mg three times daily."
)

print(r.coherent)             # False
print(r.certainty)            # "formal" — provable under stated commitments
print(r.violation["type"])    # "ModusPonensViolation"
print(r.justification)
# Lean-decidable violation (ModusPonensViolation): soundness proof in
# theory/ClosureViolation.lean. Formally certain given stated propositions.
print(r.philosophical_frame)
# Aristotle — Syllogistic logic: if P is asserted and P→Q is asserted,
# Q must hold. This action treats Q as false while both P and P→Q are
# in the commitment closure.
print(r.violation["chain"])
# [ASSERTED @ step 1] beta-lactam antibiotics are contraindicated
# [ASSERTED @ step 1] amoxicillin is a beta-lactam antibiotic
# [ACTION   @ step 3] Prescribe amoxicillin 500mg three times daily
# CONTRADICTION: action presupposes NOT(beta-lactam antibiotics contraindicated)
```

No API key needed for development:

```bash
NOUS_TEST_MODE=true python examples/scientific_usage.py
```

> PyPI release follows ArXiv submission. Use the git install for now.

---

## How It Works

Nous runs a four-phase pipeline on every agent step:

```
 Agent reasoning trace
         │
         ▼
 ┌─────────────────┐
 │  1. EXTRACT     │  Pull explicit commitments from natural language
 │  Extractor      │  "air-sensitive" → C("catalyst requires inert atmosphere")
 └────────┬────────┘
          │
          ▼
 ┌─────────────────┐
 │  2. CLOSE       │  Compute deductive closure of all commitments so far
 │  CommitmentGraph│  C(P) ∧ C(P→Q) ⟹ C(Q)   [Axiom K, Kripke 1963]
 └────────┬────────┘
          │
          ▼
 ┌─────────────────┐
 │  3. VERIFY      │  Is this action coherent with the closure?
 │  Coherence      │  act("open flask") ⊬ closure → VIOLATION
 └────────┬────────┘
          │
          ▼
 ┌─────────────────┐
 │  4. CLASSIFY    │  Which violation type? Which commitment chain broke?
 │  Detector       │  ModusPonensViolation at step 3, confidence 0.97
 └─────────────────┘
```

The commitment graph is the core data structure. Every query — assumptions, dependencies, cycles, gaps — is a graph traversal. O(V+E), no LLM needed for structure.

---

## Violation Taxonomy

Six types. Each describes a specific way an AI agent's actions diverge from the logical consequences of what it said. Each has a Lean 4 soundness proof establishing that any detected violation is a genuine breach of inferential commitment.

| ID | Plain name | Technical type | What actually happens | Lean proof |
|----|------------|----------------|-----------------------|------------|
| GT-01 | **Acting against stated knowledge** | `ModusPonensViolation` | AI commits: "beta-lactams are contraindicated." Then recommends amoxicillin — a beta-lactam. | `modusPonensSound` |
| GT-02 | **Ignoring a correction** | `BeliefRevisionFailure` | AI is told: new data contradicts the original finding. It acknowledges the update. Then keeps reasoning from the original finding as if nothing changed. | `beliefRevisionSound` |
| GT-03 | **Upgrading a guess to a fact** | `ModalScopeError` | AI says a risk "might exist." Three steps later treats that possibility as a certainty when making a decision that affects the patient. | `modalScopeSound` |
| GT-04 | **Using an expired rule** | `TemporalCoherenceViolation` | AI is given updated dosing guidelines at step 4. At step 11, it applies the original guidelines without noting the update or justifying the choice. | `temporalCoherenceSound`* |
| GT-05 | **Ignoring what two facts imply together** | `EpistemicClosureViolation` | AI knows the building requires fire suppression. Knows the design has no sprinklers. Approves the design. The conclusion was right there. | `epistemicClosureSound` |
| GT-06 | **Treating the same thing as two different things** | `ReferentialOpacityFailure` | The trustee and the beneficiary are the same person. AI gives advice appropriate for one role that violates the other — and never notices they're the same. | LLM-only (undecidable in general) |

*One `sorry` remains in the temporal proof — the abstract framework is sound but the formalization is incomplete. See [`theory/README.md`](theory/README.md).

The first four types are formally decidable given explicitly stated propositions. `ReferentialOpacityFailure` requires world knowledge and falls back to multi-model consensus (Phase D.3). The certainty tier system in `StepResult` tracks which path each violation took.

The proofs establish soundness of the *abstract framework* — every detected violation is a genuine breach of inferential commitment. They do not certify the Python detector's recall. See [`docs/RESEARCH_NOTES.md`](docs/RESEARCH_NOTES.md) for the honest account of what the formal guarantees do and do not cover.

---

## Benchmark

Evaluated on 40 annotated agent traces across 5 domains (chemistry, code, medicine, law, math):

| Metric | Nous Pipeline | Keyword Baseline |
|--------|:---:|:---:|
| **Precision** | **0.889** | 0.864 |
| Recall | 0.800 | 0.950 |
| F1 | 0.842 | 0.905 |
| False Positives | **2** | 3 |

The pipeline trades recall for precision. For a monitoring tool, false alarms are more damaging than missed detections — a noisy monitor gets ignored. `ModusPonensViolation` is detected perfectly (6/6); the main recall gap is in temporal and modal types where the commitment closure needs temporal indexing (tracked in [`docs/RESEARCH_NOTES.md`](docs/RESEARCH_NOTES.md)).

Reproduce: `bash scripts/reproduce_table1.sh`

---

## Related Work

**Self-contradiction detection** (Mundler et al., ICLR 2024) finds cases where an agent asserts `P ∧ ¬P`. Nous detects the harder case: `P` and `P→Q` are both asserted, but the agent acts as if `¬Q`. No contradiction between any two statements — the violation only appears when you compute the closure.

**SelfCheckGPT** and **Semantic Entropy** (Kuhn et al., NeurIPS 2023) detect hallucinations by comparing multiple samples against ground truth or each other. Nous requires neither ground truth nor multiple samples — it checks the agent's trace against itself.

**InferAct** (Fang et al., EMNLP 2025) and **ShieldAgent** (Chen et al., ICML 2025) use safety constraints and policy specifications. Nous uses no predefined policy — violations emerge from the agent's own stated commitments.

---

## API Reference

```python
from nous import Nous

n = Nous()

# Core: feed reasoning + action, get back coherence result
result = n.step("reasoning text", "action taken")
result.coherent     # bool
result.violation    # dict with type, chain, confidence — or None

# Query the commitment graph
s = n.state()
s.assumptions()             # beliefs asserted without proof
s.derived()                 # what follows from assertions
s.depends_on("claim")       # trace a claim back to its foundations
s.gaps_to("goal")           # what's missing to reach this conclusion
s.circular()                # cycles in the commitment graph
s.weakest_link()            # least-supported commitment
s.strength()                # 0–1 composite score
s.summary()                 # human-readable one-liner

# Hypotheticals (context-managed, auto-rolled-back)
with n.suppose("f is differentiable"):
    print(n.state().derived())  # what would follow

# Compare two reasoning paths
diff = n.diff(other_nous)
diff.only_in_left   # commitments unique to this path
diff.only_in_right  # commitments unique to the other path
diff.shared         # what both agree on

# Visualize
n.show()            # interactive Pyvis graph in browser
```

### Entailment Backends

| Backend | Cost | Speed | Notes |
|---------|------|-------|-------|
| `anthropic` (default) | ~$0.001/step | ~500ms | Claude, temperature=0 |
| `openai` | ~$0.001/step | ~400ms | GPT-4o |
| `nli` | Free | ~50ms | Local sentence-transformers, no API key |
| `test` | Free | <1ms | Deterministic fixtures for CI |

```python
n = Nous(backend="nli")     # free local model
n = Nous(provider="openai") # GPT-4o
```

---

## Integration

```python
# Any agent loop
from nous import Nous

n = Nous()
for step in agent.run():
    r = n.step(step.reasoning, step.action)
    if not r:
        agent.halt(reason=r.violation)

# LangChain
from nous.integrations.langchain import NousCallback

agent = AgentExecutor(
    agent=...,
    tools=...,
    callbacks=[NousCallback(on_violation="halt")]
)
```

---

## Architecture

```
nous/
├── __init__.py           # Nous class — the public API
├── graph.py              # CommitmentGraph — directed belief graph
├── closure.py            # Closure operator — computes C({P1,...Pn})
├── extractor.py          # Pulls commitments from natural language
├── coherence.py          # Checks action against closure
├── detector.py           # Classifies violation type
├── entailment.py         # Pluggable backends (NLI / LLM / test)
├── query.py              # Graph queries (assumptions, gaps, cycles...)
├── trace.py              # Structured audit log
├── viz.py                # Pyvis + Rich + Jupyter rendering
├── providers/            # Anthropic, OpenAI, Gemini
└── integrations/         # LangChain, generic agent loop
```

---

## Research Artifacts

| Artifact | Location |
|----------|----------|
| Paper outline + abstract | [`paper/outline.md`](paper/outline.md) |
| Lean 4 soundness proofs | [`theory/`](theory/) — build with `lake build` |
| Philosophical framework | [`docs/RESEARCH_NOTES.md`](docs/RESEARCH_NOTES.md) |
| Benchmark results (40 tasks) | [`eval/results/`](eval/results/) |
| Dataset (40 annotated traces) | [`eval/datasets/closure_tasks.json`](eval/datasets/closure_tasks.json) |
| Reproduce Table 1 | `bash scripts/reproduce_table1.sh` |
| Cite this work | [`CITATION.cff`](CITATION.cff) |

---

## Contributing

Open an issue before submitting a pull request — especially for changes to the violation taxonomy or Lean proofs, where the formal and empirical sides need to stay in sync.

The test suite runs without an API key:

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

For changes to the entailment pipeline, run the full eval to check precision/recall don't regress:

```bash
bash scripts/reproduce_table1.sh
```

---

## License

MIT © 2026 Sayan Gupta

To cite:

```bibtex
@software{gupta2026nous,
  author = {Gupta, Sayan},
  title  = {Nous: Formally-Grounded Detection of Epistemic Closure Violations in LLM Agent Reasoning Traces},
  year   = {2026},
  url    = {https://github.com/sayang7/nous}
}
```
