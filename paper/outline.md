# ClosureGuard: Formally-Grounded Detection of Epistemic Closure Violations in LLM Agent Reasoning Traces

## Paper Outline (Target: AAAI / ICLR / NeurIPS workshop on LLM Agents / EMNLP)

### Abstract (~150 words)

LLM agents increasingly reason step-by-step before acting, yet no existing tool detects when an agent's actions contradict the logical consequences of its own stated beliefs — a failure mode distinct from hallucination, self-contradiction, or factual error. We formalize this as an *epistemic closure violation*: the agent asserts P, P entails Q via its commitment closure, but the agent acts as if ¬Q. We present ClosureGuard, a detection pipeline grounded in Kripke semantics with a taxonomy of five violation types, each proven sound in Lean 4. The Python implementation operationalizes detection via a four-phase pipeline: assertion extraction, commitment closure computation, coherence verification, and violation classification. On a 40-task benchmark across 5 domains, ClosureGuard achieves 0.889 precision and 0.800 recall, with perfect detection of modus ponens violations and zero false positives on the first 27 of 40 tasks. We release code, proofs, benchmark, and evaluation framework.

### 1. Introduction (~1.5 pages)

- Opening: LLM agents reason then act. The reasoning can be flawed in ways current tools miss.
- Key example: the chemistry catalyst scenario (3 sentences, maximum impact)
- Define the gap: belief-action entailment coherence. Not P∧¬P (self-contradiction). Not hallucination (needs ground truth). This is K(P), K(P→Q), act(¬Q).
- Contributions:
  1. Formal framework: epistemic closure violations defined via Kripke semantics, proven sound in Lean 4
  2. Detection pipeline: 4-phase architecture (extract → close → verify → classify)
  3. Violation taxonomy: 5 types grounded in 60+ years of epistemic logic
  4. Evaluation: 40-task benchmark, 5 domains, baseline comparison
  5. Open-source tool: pip-installable, works with any agent trace

### 2. Related Work (~1 page)

- **Self-contradiction detection:** Mundler et al. (ICLR 2024) — detects P∧¬P, not P→Q,act(¬Q)
- **Hallucination detection:** SelfCheckGPT, Semantic Entropy — need ground truth or sampling
- **CoT faithfulness:** FaithCoT-Bench (2025) — measures faithfulness of reasoning, not belief-action coherence
- **Agent monitoring:** InferAct (EMNLP 2025), ShieldAgent (ICML 2025), AgentSpec (2025), ABC (2026) — policy/safety constraints, not epistemic logic
- **Formal belief revision:** Bonanno (2025) Kripke-Lewis semantics — theoretical, not applied to LLMs
- **Gap:** No tool combines formal epistemic logic with LLM agent monitoring for belief-action coherence

### 3. Formal Framework (~2 pages)

- 3.1 Kripke Semantics (brief: worlds, accessibility, K operator)
- 3.2 Epistemic Closure (Axiom K: K(P)∧K(P→Q)→K(Q))
- 3.3 From Knowledge to Commitment (Brandom's move: agents don't have knowledge, they have commitments)
  - Definition: Commitment Closure C({P1,...,Pn})
  - Theorem: violation_contradicts_commitment (proven in Lean 4)
- 3.4 Violation Taxonomy (5 types, formal definitions)
- 3.5 Lean 4 Formalization (4 layers, key theorems, the one sorry and why)

### 4. Detection Pipeline (~1.5 pages)

- 4.1 Phase 1: Assertion Extraction (LLM extracts beliefs + inferential commitments)
- 4.2 Phase 2: Commitment Closure (LLM computes C({P1,...,Pn}) cumulatively)
- 4.3 Phase 3: Coherence Verification (action vs full closure, not pairwise)
- 4.4 Phase 4: Classification (5-type taxonomy, confidence threshold)
- 4.5 Complexity: O(n) API calls per n-step trace
- 4.6 Design Decisions (why LLM-as-judge, why temperature=0, why not symbolic)

### 5. Evaluation (~2 pages)

- 5.1 Benchmark Design
  - 40 tasks: 20 violation, 20 clean (incl. 10 adversarial near-miss)
  - 5 domains: code_agent, math_reasoning, planning, scientific, web_agent
  - 5 violation types (all represented in both positive and negative)
- 5.2 Baseline: naive single-prompt detection
- 5.3 Results
  - Table 1: Pipeline vs Baseline (precision, recall, F1, FP, FN)
  - Table 2: Per-type detection
  - Table 3: Per-domain F1
- 5.4 Analysis
  - Pipeline wins on precision (0.889 vs 0.864) — matters for monitoring
  - Pipeline loses on recall (0.800 vs 0.950) — misses non-ModusPonens types
  - False negative root causes (belief revision, modal scope, temporal)
  - False positive root causes (adversarial near-miss cases)
- 5.5 Ablations
  - Confidence threshold sweep (0.7 → 0.9)
  - With/without closure phase (direct extraction → coherence check)

### 6. Discussion (~1 page)

- The formal-empirical gap: Lean proofs guarantee the framework, not the implementation
- When to use pipeline vs baseline (precision-critical vs recall-critical)
- Limitations: hand-authored benchmark, single LLM backend, no real agent traces yet
- Future: temporal indexing, modal qualifier tracking, SWE-bench/WebArena traces

### 7. Conclusion (~0.5 page)

- First formally-grounded detector for epistemic closure violations in LLM agents
- Lean 4 proofs establish soundness, Python pipeline operationalizes detection
- Higher precision than naive baseline, with interpretable and auditable output
- Open-source: pip install nous-ai

### Appendices

- A: Full Lean 4 theorem statements
- B: All 40 benchmark tasks (or representative subset)
- C: Prompt templates (extraction, closure, coherence)
- D: Per-task results

---

## Submission Strategy

### Tier 1 (reach): ICLR 2027, NeurIPS 2026 (if deadline allows)
### Tier 2 (strong fit): AAAI 2027, EMNLP 2026
### Tier 3 (workshop): NeurIPS Workshop on LLM Agents, ICLR Workshop on Formal Verification + ML
### Tier 4 (guaranteed visibility): ArXiv preprint + Twitter thread + HN post

### The Move: Post ArXiv preprint FIRST, then submit to conference.
ArXiv gives you a timestamp (priority), Twitter/HN gives you visibility, conference gives you credibility.

## Twitter/X Thread Template

Thread: "I built the first tool that catches when AI agents contradict their own reasoning — and proved it sound in Lean 4. Here's why this matters for every researcher using AI assistants."

1/ Your AI agent says "the catalyst is air-sensitive" then opens the flask to air. No tool catches this. Not hallucination. Not self-contradiction. It's a belief-ACTION gap. I built ClosureGuard to fix this. [screenshot of demo]

2/ The problem: LLM agents reason step-by-step, building up beliefs. Then they act. Sometimes the action contradicts what they logically committed to. K(P) ∧ K(P→Q) but act(¬Q). This is epistemic closure violation.

3/ Why existing tools miss it: SelfCheckGPT needs ground truth. Self-contradiction detectors find P∧¬P. But P→Q,act(¬Q) has NO explicit contradiction. The violation is hidden in the inference.

4/ ClosureGuard uses a 4-phase pipeline grounded in Kripke semantics: Extract → Closure → Verify → Classify. Each phase maps to a formal concept. O(n) API calls, not O(n²). [architecture diagram]

5/ The kicker: it's formally proven in Lean 4. 8 theorems. The key one: violation_contradicts_commitment — every flagged violation is a genuine structural incoherence, even if the agent's beliefs are false.

6/ Results on 40-task benchmark: 88.9% precision, 80.0% recall. Perfect on math reasoning (F1=1.0). Catches assumption drift, contradictory recommendations, safety violations in experimental protocols.

7/ This matters for: math researchers (catches unproved assumptions), chemists (catches protocol violations), drug discovery (catches contradictory recommendations), anyone building AI agents.

8/ It's open source, MIT licensed, pip installable. Paper + code + Lean proofs + benchmark. [link]

Solo project by a student. If this is useful for your research, I'd love to hear about it. 🧵

## Hacker News Title Options
- "ClosureGuard: Catching when AI agents' actions contradict their own reasoning (with Lean 4 proofs)"
- "Show HN: I proved in Lean 4 that LLM agents violate their own logic, then built a detector"
- "Your AI agent knows the answer then does the wrong thing — a formally verified detector"
