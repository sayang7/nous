# Contributing to Nous

Thanks for your interest. A few things to know before you send a PR.

## Before opening a PR

Open an issue first for anything non-trivial. This is especially important for:

- Changes to the violation taxonomy (GT-01 through GT-05) — these touch the Lean proofs, the Python classifier, the benchmark dataset, and the paper simultaneously
- New entailment backends — needs precision/recall validation against the 40-task benchmark
- Changes to the commitment closure algorithm in `nous/closure.py` — the formal guarantees in `theory/` need to stay in sync

For typos, doc fixes, and example improvements, a PR is fine without a prior issue.

## Setup

```bash
git clone https://github.com/sayang7/nous
cd nous
pip install -e ".[dev]"
pytest tests/ -v
```

All tests run without an API key. The test suite uses deterministic fixtures.

## Running the full benchmark

Changes to the detection pipeline should be validated against the 40-task benchmark:

```bash
export ANTHROPIC_API_KEY=your_key
bash scripts/reproduce_table1.sh
```

The target is: precision ≥ 0.889, recall ≥ 0.800, F1 ≥ 0.842. Regressions in precision are treated as bugs.

## Lean proofs

If you add a new violation type, you need a corresponding Lean theorem in `theory/ClosureViolation.lean`. The theorem must establish soundness: if the system reports a violation of this type, the agent's commitments are genuinely incoherent.

Build the proofs:

```bash
lake build
```

One existing `sorry` in `temporalCoherenceSound` is tracked and known. New `sorry`s are not accepted.

## Code style

- Type annotations on all public functions
- Docstrings on all public classes and functions
- `temperature=0` on all API calls (non-negotiable — reproducibility depends on it)
- No dependencies outside `requirements.txt` without discussion

## Questions

Open an issue or email sayan.gupta200@gmail.com.
