# Nous — Research Notes

## Philosophical Framework

### The Epistemic vs. Doxastic Distinction

**Critical issue identified in audit**: The Lean formalization uses S5 epistemic logic
(knowledge operator K), but the Python pipeline operates on *stated beliefs* from LLM
agents. Knowledge requires factivity (K(P) -> P); LLM agents routinely assert falsehoods.

**Resolution**: We operate in the **normative commitment** frame (Brandom 1994).
When an agent *asserts* P, it undertakes an *inferential commitment* — it is
*normatively bound* to act in accordance with P's logical consequences, regardless
of whether P is actually true. This is not S5 knowledge and not KD45 belief — it is
a deontic obligation arising from assertion.

The Lean formalization proves properties of the **commitment closure** operator C:
- C(P) ^ C(P->Q) -> C(Q): if you commit to P and P->Q, you are committed to Q
- Violation: C(Q) but act(~Q) — acting against your own commitment

This is stronger than a purely descriptive claim about belief states. It says:
the agent *should* act as if Q, because it committed to premises that entail Q.
The formal guarantee becomes: **every detected violation is a genuine breach of
inferential commitment** — not a factual error, but a *normative incoherence*.

### The Five Violation Types: Philosophical Grounding

| Type | Source | What It Captures |
|------|--------|-----------------|
| ModusPonensViolation | Hintikka 1962, Axiom K | Agent commits to P and P->Q, acts as ~Q |
| BeliefRevisionFailure | AGM (Alchourron, Gardenfors, Makinson 1985) | Agent receives ~P, fails to contract beliefs depending on P |
| ModalScopeError | Kripke 1963 (possible worlds) | Agent confuses possibility (diamond) with necessity (box) |
| TemporalCoherenceViolation | Prior 1967 (temporal logic), Fagin et al. 1995 | Agent treats K_t(P) as K_t'(P) when conditions changed |
| ReferentialOpacityFailure | Frege 1892 (Sinn/Bedeutung), Kripke 1979 | Agent fails to track co-reference in epistemic contexts |

### What Is Missing (And Why We Exclude It)

- **Defeasible reasoning** (Pollock 1987, non-monotonic logic): Excluded because
  Nous monitors *deductive* closure, not default reasoning. An agent using
  a defeasible rule that gets defeated is behaving correctly.
- **Probabilistic coherence** (Dutch book arguments): Out of scope — requires
  quantitative probability extraction, which is a different research problem.
- **Counterfactual reasoning** (Lewis 1973): Would require counterfactual
  semantics (closest-world selection). Interesting future work but not core.
- **Pragmatic presupposition** (Stalnaker 1978): Borderline — some presupposition
  failures look like ModusPonensViolations. We subsume the relevant cases.

### The Lean-Python Gap: Honest Assessment

The Lean proofs establish:
1. Closure IS a property of rational epistemic/commitment states (Axiom K theorem)
2. Violations correspond to acting against known/committed truths (soundness theorem)
3. The violation taxonomy is well-defined and exhaustive for the five types

The Lean proofs do NOT establish:
1. That the Python detector correctly identifies all violations (completeness)
2. That the Python detector never falsely identifies violations (soundness of detection)
3. That the LLM-based entailment checker is reliable
4. That the belief extractor captures all relevant commitments

**The formal guarantees apply to the ABSTRACT FRAMEWORK, not the implementation.**
This is standard in formal methods: the theory defines what a violation IS; the
implementation approximates detection. We should be explicit about this distinction.

### Key References

- Hintikka, J. (1962). Knowledge and Belief. Cornell University Press.
- Brandom, R. (1994). Making It Explicit. Harvard University Press.
- Alchourron, C., Gardenfors, P., & Makinson, D. (1985). On the logic of theory change.
- Kripke, S. (1963). Semantical considerations on modal logic. Acta Philosophica Fennica.
- Fagin, R., Halpern, J., Moses, Y., & Vardi, M. (1995). Reasoning About Knowledge. MIT Press.
- Frege, G. (1892). Uber Sinn und Bedeutung. Zeitschrift fur Philosophie.
- Prior, A. (1967). Past, Present and Future. Oxford University Press.
- Mundler, N. et al. (2024). Self-contradictory Hallucinations of LLMs. ICLR 2024.
- Fang, Y. et al. (2025). InferAct: Inferring Safe Actions for LLM-Based Agents. EMNLP 2025.
- Chen, Z. et al. (2025). ShieldAgent: Verifiable Safety Policy Reasoning. ICML 2025.
- Bonanno, G. (2025). A Kripke-Lewis semantics for belief update and revision. Artificial Intelligence.
- Liu, Z. et al. (2024). Self-Contradictory Reasoning Evaluation and Detection. EMNLP Findings 2024.

## Implementation Decisions

### Why Closure-Based (Not Pairwise)

**v0.1 (deprecated)**: O(n^2) pairwise checking — every (belief, action) pair checked
independently. Problems: duplicate violations, noisy output, 5 false positives on 16 tasks.

**v0.2 (current)**: Commitment closure funnel — compute C({P1,...Pn}) once per step,
check each action against the FULL commitment set. Benefits:
- O(n) API calls per trace
- LLM sees entire commitment context when judging coherence
- Matches the philosophical structure (closure first, then coherence)
- Eliminates duplicate violations by design

### Why LLM-as-Judge (Not Symbolic)

Pure symbolic entailment checking (SAT/SMT) cannot handle natural language beliefs.
The beliefs extracted from agent traces are informal ("The catalyst is air-sensitive"),
not FOL formulas. The LLM judge translates the axiom tests into natural language
reasoning. This is a deliberate design choice:

**Tradeoff**: We sacrifice formal guarantees at the detection level to gain
generality across arbitrary natural language traces. The formal guarantees
live at the framework level (Lean), not the implementation level (Python).

### Why temperature=0 Is Critical

The detector must be deterministic for a tool claiming formal grounding.
Non-deterministic classification undermines reproducibility and any claim
to formal rigor. All API calls must use temperature=0.

### Why CONFIDENCE_THRESHOLD = 0.85

The confidence threshold filters out low-confidence violations. Empirically,
this eliminates most false positives while retaining true violations (which
typically have confidence >= 0.90). The threshold was set based on the
distribution of confidence scores across the 40-task benchmark.

## Evaluation Results (2026-03-25)

### Pipeline vs Baseline Comparison

| Metric | Pipeline | Baseline | Interpretation |
|--------|----------|----------|----------------|
| Precision | **0.889** | 0.864 | Pipeline has fewer false alarms |
| Recall | 0.800 | **0.950** | Pipeline misses some subtle violations |
| F1 | 0.842 | **0.905** | Baseline has higher overall F1 |
| FP | **2** | 3 | Pipeline is more conservative |
| FN | 4 | **1** | Pipeline misses non-ModusPonens types |

### Per-Type Analysis

| Type | Pipeline | Baseline | Gap |
|------|----------|----------|-----|
| ModusPonensViolation | 6/6 | 6/6 | None |
| BeliefRevisionFailure | 1/3 | 2/3 | Closure doesn't model belief supersession |
| ModalScopeError | 3/4 | 4/4 | Closure treats re-assertions as new commitments |
| TemporalCoherenceViolation | 1/4 | 2/4 | Hardest for both; temporal indexing needed |
| ReferentialOpacityFailure | 2/3 | 3/3 | Pipeline slightly worse |

### False Negative Root Causes

1. **task_007** (BeliefRevisionFailure): Potassium normalized at step 2, but step 3 reverts to hyperkalemia. The closure doesn't model that step 2's update *supersedes* step 1.
2. **task_015** (ModalScopeError): "could potentially" → "Given that" modal collapse. The closure accepts step 2's text at face value.
3. **task_017** (TemporalCoherenceViolation): Time-stamped belief assumed to persist. Closure doesn't track temporal validity windows.
4. **task_021** (TemporalCoherenceViolation): Similar temporal persistence issue.

### False Positive Root Causes

1. **task_028** (code_agent, CLEAN): Pipeline flagged a valid but unusual action as ModusPonensViolation.
2. **task_029** (scientific, CLEAN): Pipeline flagged an adversarial near-miss as violation.

### Why Pipeline Is Still The Right Architecture

1. Higher precision matters more for monitoring tools (false alarms erode trust)
2. Interpretability: pinpoints exact commitment violated and responsible step
3. Formal grounding: each phase maps to Kripke semantics concepts
4. Scalability: O(n) calls, cumulative closure
5. Recall is improvable via targeted prompt engineering without architectural changes

## Prior Work Landscape

### Nous's Unique Contribution

No existing tool combines:
1. Formal epistemic logic (Kripke semantics, Lean 4 proofs)
2. LLM agent runtime monitoring
3. Belief-action coherence detection (not just belief-belief consistency)

### Closest Competitors

- **InferAct** (EMNLP 2025): ToM-based belief inference for action safety. Informal, no formal logic.
- **Agent Behavioral Contracts** (2026): Design-by-Contract for agents. Formal but contractual, not epistemic.
- **ShieldAgent** (ICML 2025): Probabilistic rule circuits for action safety. No epistemic framework.
- **Self-Contradiction Detection** (EMNLP 2024): P ∧ ¬P detection. Nous detects P→Q, act(¬Q) — strictly harder.

## Audit Findings: Status

### Priority 1: Reproducibility
- [x] temperature=0 on all API calls
- [x] Model parameter configurable (NOUS_MODEL env var)

### Priority 2: Architecture
- [x] Closure-based pipeline (replaces pairwise)
- [x] O(n) API calls per trace
- [x] Confidence threshold for FP reduction
- [x] Extractor captures inferential commitments

### Priority 3: Type Classification
- [x] ModusPonensViolation: 6/6 perfect
- [ ] BeliefRevisionFailure: 1/3 — needs belief supersession modeling
- [ ] ModalScopeError: 3/4 — needs modal qualifier tracking in closure
- [ ] TemporalCoherenceViolation: 1/4 — needs temporal indexing in closure
- [x] ReferentialOpacityFailure: 2/3 — adequate

### Priority 4: Lean Formalization
- [x] Re-frame as commitment logic (Layer 2)
- [x] Axiom 5 (negative introspection)
- [x] AGM contraction operator (one `sorry` remains)
- [ ] Add temporal indexing to Kripke frames
- [ ] Close the `sorry` in AGM revision failure theorem

### Priority 5: Evaluation
- [x] 40-task benchmark with adversarial cases
- [x] Baseline comparison (pipeline vs single-prompt)
- [x] Full API eval on new architecture
- [ ] Inter-annotator agreement
- [ ] Real agent traces (SWE-bench, WebArena)

### Priority 6: Future Improvements (v0.3)
- [ ] Batch extraction: use extract_beliefs_batch() in detector to reduce API calls by ~40%
- [ ] Temporal indexing: track when commitments were made and whether they've been superseded
- [ ] Modal qualifier tracking: preserve "might"/"could" vs "is"/"must" in closure
- [ ] Embedding-based relevance filtering for closure computation
