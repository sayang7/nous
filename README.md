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

An AI agent says *"the catalyst is air-sensitive"* then opens the flask to air. No existing tool catches this.

It isn't a hallucination — the agent never claims the flask is safe. It isn't self-contradiction — neither statement says anything about the other. It is a **belief-action gap**: the agent held a commitment (`air-sensitive → stay under nitrogen`) and acted against it without retracting the commitment first.

Formally: `K(P) ∧ K(P → Q) ∧ act(¬Q)`.

Nous detects this. SelfCheckGPT needs ground truth. Contradiction detectors find `P ∧ ¬P`. Nous finds the hidden violation where an agent's *action* breaks the logical closure of its *own stated beliefs*.

---

## Quick Start

```bash
pip install git+https://github.com/sayang7/nous
```

```python
from nous import Nous

n = Nous()
n.step("The catalyst is air-sensitive. Exposure to oxygen deactivates it.", "Note requirement.")
n.step("Transfer catalyst under nitrogen.", "Transfer catalyst.")
r = n.step("Open flask to air to add reagent.", "Add reagent.")

print(r.coherent)   # False
print(r.violation)  # {'type': 'ModusPonensViolation', 'chain': [...]}
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

Five types, each grounded in a specific tradition of formal logic with Lean 4 soundness proofs:

| ID | Type | Philosopher | What It Catches | Lean Theorem |
|----|------|-------------|-----------------|--------------|
| GT-01 | `ModusPonensViolation` | Hintikka (1962) — Axiom K | Agent commits to P and P→Q, acts as ¬Q | `modusPonensSound` |
| GT-02 | `BeliefRevisionFailure` | AGM (1985) | New evidence received, contradicted prior belief persists | `beliefRevisionSound` |
| GT-03 | `ModalScopeError` | Kripke (1963) | Necessity (□) treated as possibility (◇) or vice versa | `modalScopeSound` |
| GT-04 | `TemporalCoherenceViolation` | Prior (1967) | Belief from time T₁ applied at T₂ without revalidation | `temporalCoherenceSound`* |
| GT-05 | `ReferentialOpacityFailure` | Frege (1892) | Co-referential substitution inside a belief context | LLM-only (undecidable) |

*One `sorry` remains in the temporal proof. See [`theory/README.md`](theory/README.md) for details.

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
