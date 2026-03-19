# ClosureGuard

**Detecting Epistemic Closure Violations in LLM Agent Reasoning Traces**

## Abstract

Large language model agents routinely violate epistemic closure: they state a belief P, state or imply that P entails Q, and then act as though Q is unknown or false. This is not a factual error or a self-contradiction — it is a structural incoherence between stated beliefs and downstream actions. ClosureGuard is the first formal framework for detecting these violations. Grounded in Hintikka's epistemic logic (K(P) ∧ K(P→Q) → K(Q)) and Brandom's inferential role semantics, we formalize five violation types in Lean 4, implement a detection pipeline using entailment checking, and evaluate on a curated dataset of reasoning traces. On our 10-task benchmark, the detector achieves F1 = 1.00 with correct type classification for all violation categories. The formal definitions typecheck in Lean 4 with complete proofs (no `sorry`).

## Distinction from Prior Work

**This is NOT self-contradiction detection.** Mündler et al. (ICLR 2024) detect cases where an agent says P and then says ¬P. ClosureGuard detects a fundamentally different failure: the agent says P, P entails Q, and the agent then *acts* as though ¬Q — without ever explicitly denying P or Q. In all five of our violation-positive benchmark cases, no two sentences in the trace directly contradict each other. A sentence-level contradiction detector would score these traces as fully consistent.

**This is NOT behavioral consistency.** Cross-run stochasticity (different outputs for the same prompt) is a separate phenomenon driven by sampling variance. ClosureGuard operates on a *single* reasoning trace, detecting structural incoherence in the agent's inferential commitments within that trace. Following Brandom, we treat the agent's outputs as assertions carrying inferential obligations — the question is whether those obligations are honored in subsequent actions, not whether the agent is deterministic across runs.

**The specific gap we address:** belief-action entailment coherence within a single trace. An agent's stated beliefs form an inferential web; its actions either honor or violate that web. ClosureGuard makes this gap formally detectable and empirically measurable.

## Architecture

### Formal Theory (`theory/`)

Lean 4 definitions establishing the formal foundation. Defines `Belief`, `AgentStep`, `ReasoningTrace`, and `EntailmentRelation` as core types. The `EpistemicallyClosed` predicate captures Hintikka's closure condition over belief sets. The `ViolationType` inductive type formalizes our five-category taxonomy. Two theorems — `violation_implies_incoherence` and `violation_witness_breaks_closure` — are proven without `sorry`, establishing that any violation witness is a constructive counterexample to epistemic closure.

### Belief Extractor (`closureguard/extractor.py`)

Extracts explicit beliefs and commitments from agent step text. Uses Claude API (claude-sonnet-4-6) with a constrained system prompt that returns only explicitly stated beliefs as a JSON array. Includes a complete test fixture set for offline evaluation without API access.

### Entailment Checker (`closureguard/checker.py`)

Determines whether believing A commits an agent to believing B. Returns both a boolean entailment judgment and a confidence score. Results are cached to avoid redundant API calls. The checker operates on belief-belief pairs and belief-action pairs — the latter is critical for detecting the belief-action gap.

### Violation Detector (`closureguard/detector.py`)

The main pipeline. For each step in a trace: extracts beliefs, checks entailments against all prior beliefs AND against the step's action (treated as an implicit belief), and classifies detected violations into the five-type taxonomy. Deduplicates violations by (step, antecedent, type). Returns structured `ClosureViolationReport` objects with step index, belief pair, violation type, and confidence score.

### Scorer (`closureguard/scorer.py`)

Computes aggregate `ClosureMetrics` from a list of violations: closure score (violations/steps, bounded [0,1]), violation count, per-type breakdown, and most common violation type.

## Violation Taxonomy

```
inductive ViolationType where
  | ModusPonensViolation         -- stated P, stated P→Q, acted as ¬Q
  | BeliefRevisionFailure        -- new evidence contradicts prior P, P not updated
  | ModalScopeError              -- confused "possible" (◇) with "necessary" (□)
  | TemporalCoherenceViolation   -- committed to P-at-t₁, acted ¬P-at-t₁ later
  | ReferentialOpacityFailure    -- treated co-referential terms as distinct
```

## Quick Start

Requires Python 3.11+ and (optionally) Lean 4 for formal verification.

```bash
git clone https://github.com/sayangupta/ClosureGuard.git
cd ClosureGuard
pip install -r requirements.txt

# Run evaluation (works without API key using test fixtures)
python eval/run_eval.py

# Expected output: F1 = 1.00, all 10 tasks PASS

# Run tests
python -m pytest tests/ -v

# (Optional) Verify Lean 4 formal definitions
lake build
```

To run with live Claude API inference instead of test fixtures:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python eval/run_eval.py
```

## Lean 4 Formal Definitions

The formal theory is in [`theory/ClosureViolation.lean`](theory/ClosureViolation.lean). Key definitions:

- `EpistemicallyClosed` — a belief set is closed under entailment
- `ClosureViolation` — a record witnessing a specific violation
- `ViolationType` — the five-category taxonomy
- `TraceEpistemicallyClosed` — closure condition lifted to reasoning traces
- `violation_implies_incoherence` — proven theorem: any violation witness refutes closure
- `violation_witness_breaks_closure` — proven corollary with content-distinctness

All definitions typecheck with `lake build` on Lean 4 v4.16.0. Both theorems have complete proofs.

## Evaluation Results

On the included 10-task benchmark (5 violation-positive, 5 violation-negative):

| Metric    | Value |
|-----------|-------|
| Precision | 1.000 |
| Recall    | 1.000 |
| F1        | 1.000 |

Per-violation-type detection: ModusPonensViolation 2/2, BeliefRevisionFailure 1/1, ModalScopeError 1/1, TemporalCoherenceViolation 1/1.

## Citation

```bibtex
@misc{closureguard2026,
  title={ClosureGuard: Detecting Epistemic Closure Violations in LLM Agent Reasoning},
  author={Gupta, Sayan},
  year={2026},
  url={https://github.com/sayangupta/ClosureGuard}
}
```

## License

MIT
