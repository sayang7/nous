# Paper

**Title:** Nous: Formally-Grounded Detection of Epistemic Closure Violations in LLM Agent Reasoning Traces

**Status:** Draft in progress

**Target venues:** AAAI 2027 / ICLR 2027 workshop on LLM Agents / NeurIPS 2026 workshop / EMNLP 2026

**Contact:** Sayan Gupta — [github.com/sayang7](https://github.com/sayang7)

---

## Files

- `outline.md` — Full paper skeleton with section outlines, abstract, Twitter thread draft, and HN post options
- `figures/` — Architecture diagram, frontend screenshot, benchmark charts (in progress)
- `main.tex` — LaTeX source (coming soon — will be generated from outline.md)
- `references.bib` — Bibliography (coming soon)

## Reading the Outline

`outline.md` contains:
1. Abstract (finalized)
2. Section-by-section outlines with key claims
3. Benchmark numbers (Table 1: F1=0.842, P=0.889, R=0.800)
4. Related work analysis (SelfCheckGPT, FaithCoT-Bench, InferAct, ShieldAgent)
5. Twitter thread draft (8 tweets)
6. Hacker News title options

## Key Claims

| Claim | Evidence |
|-------|----------|
| F1 = 0.842 on 40-task benchmark | `eval/results/run_20260325_121634.json` |
| Precision = 0.889 | Same file |
| ModusPonensViolation: 6/6 detected | Same file, `type_breakdown` |
| Lean 4 soundness proofs | `theory/ClosureViolation.lean` |
| 5 violation types, formally grounded | `nous/violations/` + `theory/` |

## Reproducing Results

```bash
bash scripts/reproduce_table1.sh
```
