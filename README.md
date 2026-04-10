<p align="center">
  <h1 align="center">Nous (νοῦς)</h1>
  <p align="center"><strong>Computational Reasoning Engine.<br>Makes thought inspectable, queryable, forkable, and comparable.</strong></p>
</p>

<p align="center">
  <a href="#the-idea">The Idea</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#what-you-can-do">Capabilities</a> &bull;
  <a href="#why-this-is-new">Why New</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#lean-4-proofs">Lean 4 Proofs</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/lean-4.16.0-orange.svg" alt="Lean 4">
  <img src="https://img.shields.io/badge/tests-98%20passed-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
</p>

---

## The Idea

When a researcher uses AI to reason through a hard problem — a proof, a hypothesis, a protocol — the reasoning is just text. You can't see its structure, can't query its assumptions, can't fork it to explore alternatives, can't compare two approaches, can't find what's missing.

**Nous makes reasoning into a computational object.**

Like databases made text queryable. Like git made code branchable. Nous makes thought inspectable, queryable, forkable, and comparable.

```python
from nous import Nous

n = Nous()

# Feed it reasoning (any source — human, AI, mixed)
n.step("f is continuous on [a,b]", "Apply IVT")
n.step("By IVT, root exists in (a,b)", "Find root")

# SEE the structure
n.state().assumptions()     # What's asserted without proof
n.state().derived()         # What follows from assertions
n.state().depends_on("root exists")  # Trace back to foundations

# QUERY the structure
n.state().gaps_to("f is differentiable")  # What's missing to reach this?
n.state().circular()        # Any circular reasoning?
n.state().weakest_link()    # Which commitment has least support?

# MANIPULATE the structure
with n.suppose("f is differentiable"):
    print(n.state().derived())        # See consequences
    print(n.state().circular())       # Any problems?
# Auto-rolled back — original state preserved

# COMPARE structures
diff = n.diff(other_nous)  # How do two reasoning paths differ?

# VERIFY the structure
r = n.step("Since f is differentiable...", "Find extrema")
r.coherent          # False — differentiability never proven
r.violation          # Exact path showing the gap
```

**3 methods at core:** `step()`, `state()`, `closure()`. Everything else is a query on the graph.

---

## Quick Start

```bash
pip install git+https://github.com/sayang7/nous
```

> PyPI release coming after ArXiv submission. Use the git install above for now.

### Detect a violation

```python
from nous import Nous

n = Nous()
n.step("The catalyst is air-sensitive. Exposure to oxygen deactivates it.",
       "Note requirements.")
n.step("Transfer catalyst under nitrogen.",
       "Transfer catalyst.")
r = n.step("Open flask to air to add reagent.",
           "Add reagent.")

print(r)            # Step 3: INCOHERENT — ModusPonensViolation
print(r.coherent)   # False
print(r.violation)  # {'type': 'ModusPonensViolation', 'chain': '...', ...}

if not r:           # StepResult is falsy when incoherent
    print("Reasoning broke down!")
```

### Visualize the graph

```python
n.show()            # Opens interactive Pyvis graph in browser
                    # Violations glow red. Nodes are draggable.

# In Jupyter notebooks, just display the object:
n                   # Renders inline HTML automatically via _repr_html_()
```

### Audit the trace

```python
for entry in n.trace():
    print(entry)
# [step 1] >>> Processing: The catalyst is air-sensitive...
# [step 1]   + 2 commitment(s) extracted
# [step 1]   = Closure: 3 commitments
# [step 1]   ✓ Step coherent
# [step 3]   ✗ VIOLATION: ModusPonensViolation — ...
```

### Measure reasoning strength

```python
s = n.state()
print(s.summary())   # [INCOHERENT] 5 assumptions, 2 derived, 3 edges, 1 violation(s), strength=70%
print(s.strength())  # 0.7  (0-1 score combining coverage, confidence, cycles, violations)
```

### Explore hypotheticals

```python
n = Nous()
n.step("All known metals conduct electricity.", "Record property.")

with n.suppose("Suppose we discover a non-conducting metal"):
    # What would the consequences be?
    s = n.state()
    print(s.assumptions())  # Includes the hypothetical
    # Original state preserved after exiting
```

### Compare two reasoning paths

```python
approach_a = Nous()
approach_a.step("Use binary search", "Search")
approach_a.step("Array must be sorted", "Verify precondition")

approach_b = Nous()
approach_b.step("Use linear scan", "Search")
approach_b.step("Works on any array", "No precondition needed")

diff = approach_a.diff(approach_b)
print(diff.only_in_left)   # Commitments unique to approach A
print(diff.only_in_right)  # Commitments unique to approach B
print(diff.shared)          # What both approaches agree on
```

### Free core (no API needed)

The graph algorithms — assumptions, derived, depends_on, circular, weakest_link, suppose, diff, strength — are pure computation. No LLM calls. The only part that needs an API is extracting beliefs from natural language.

```python
n = Nous(backend="nli")  # Free local NLI model for entailment
# Or use test_mode=True for development
```

---

## What You Can Do

| Capability | Method | Cost | Grounded In |
|-----------|--------|------|------------|
| See assumptions | `state().assumptions()` | Free | Brandom (inferential role) |
| See derived commitments | `state().derived()` | Free | Commitment closure |
| Trace dependencies | `state().depends_on(P)` | Free | Kripke (accessibility) |
| Find gaps | `state().gaps_to(goal)` | Free | Peirce (abduction) |
| Detect cycles | `state().circular()` | Free | Tarjan's SCC, O(V+E) |
| Find weakest link | `state().weakest_link()` | Free | Confidence propagation |
| Measure strength | `state().strength()` | Free | Composite score |
| Summarize state | `state().summary()` | Free | Human-readable |
| Explore hypotheticals | `suppose(P)` | Free | Kripke (possible worlds) |
| Compare reasoning | `diff(other)` | Free | Gentner (structure mapping) |
| Detect violations | `step(reasoning, action)` | 1 API call | Graph traversal + entailment |
| Visualize graph | `show()` | Free | Pyvis (vis.js) |
| Jupyter rendering | `_repr_html_()` | Free | Inline HTML |
| Audit trail | `trace()` | Free | Structured event log |
| Export graph | `export_dot()` | Free | Graphviz DOT |

---

## Why This Is New

| What Exists | What Nous Does Instead |
|------------|----------------------|
| Lean/Coq: formal proofs for math | Formal structure for ANY reasoning |
| LLM CoT: opaque text stream | Inspectable graph with queryable structure |
| Graph of Thoughts: paper concept | Deployed tool with real API |
| Guardrails AI: validate output format | Make the reasoning ITSELF queryable |
| AlphaProof: solve competition math | Help researchers explore and strengthen arguments |

**No deployed tool** takes informal reasoning, extracts its logical structure, and makes it a first-class computational object you can inspect, query, manipulate, fork, and compare.

---

## Architecture

```
nous/
├── __init__.py       # Nous class (3-method API + query surface)
├── graph.py          # CommitmentGraph (THE core data structure)
├── query.py          # Structural queries (pure graph algorithms)
├── entailment.py     # Pluggable backends (NLI/embed/LLM)
├── extractor.py      # Belief extraction from natural language
├── trace.py          # Reasoning trace for auditability
├── viz.py            # Visualization (Pyvis, Rich, Jupyter)
├── providers/        # Any-LLM support (Anthropic, OpenAI)
└── integrations/     # LangChain, generic agent loops
```

### Entailment Backends

| Backend | Cost | Speed | Accuracy | Install |
|---------|------|-------|----------|---------|
| NLI (recommended) | Free | ~50ms/check | ~90% MNLI | `pip install nous-ai[nli]` |
| Embedding | Free | ~10ms/check | ~75% | `pip install nous-ai[nli]` |
| LLM (Claude) | ~$0.001/check | ~500ms | ~95% | Set `ANTHROPIC_API_KEY` |

### LLM Providers

```python
n = Nous(provider="anthropic")  # Claude (default)
n = Nous(provider="openai")     # GPT-4
n = Nous(backend="nli")         # Free, no LLM for entailment
```

---

## Lean 4 Proofs

The violation taxonomy is formally verified in Lean 4:

- **Soundness**: if the system reports a violation, the trace is genuinely incoherent
- **Completeness**: every form of incoherence maps to exactly one violation type
- **Closure properties**: the commitment closure operator is monotone and idempotent

See `theory/` for the full Lean 4 development.

---

## Evaluation

On a 40-task benchmark spanning math, science, coding, and mixed-domain reasoning:

| Metric | Score |
|--------|-------|
| F1 | 0.842 |
| Precision | 0.889 |
| Recall | 0.800 |

The system catches real violations with high precision while avoiding false alarms.

---

## Integration

### Direct (Recommended)

```python
from nous import Nous

n = Nous()
for step in agent.run():
    r = n.step(step.reasoning, step.action)
    if not r:  # StepResult is falsy when incoherent
        print(f"Violation: {r.violation['type']}")
        print(f"Chain: {r.violation['chain']}")
```

### LangChain

```python
from nous.integrations.langchain import NousCallback

callback = NousCallback(on_violation="halt")
agent = AgentExecutor(agent=..., tools=..., callbacks=[callback])
```

### Any Agent Loop

```python
from nous.integrations.generic import guard_agent_loop

for step, result in guard_agent_loop(agent.stream()):
    if not result:
        agent.stop()
        break
```

---

## Research Artifacts

| Artifact | Location |
|----------|----------|
| Paper outline + abstract | [`paper/outline.md`](paper/outline.md) |
| Lean 4 soundness proofs | [`theory/README.md`](theory/README.md) |
| Benchmark results (40 tasks) | [`eval/results/README.md`](eval/results/README.md) |
| Dataset schema + domain breakdown | [`eval/datasets/README.md`](eval/datasets/README.md) |
| Reproduce Table 1 | `bash scripts/reproduce_table1.sh` |
| Cite this work | [`CITATION.cff`](CITATION.cff) |

## License

MIT
