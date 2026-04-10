# Benchmark Results

This directory contains the raw output files from Nous evaluation runs. All results are committed to enable independent verification of the claims in the paper.

## Primary Result (Table 1)

**File:** `run_20260325_121634.json`

| Metric | Value |
|--------|-------|
| Precision | 0.889 |
| Recall | 0.800 |
| F1 | 0.842 |
| True Positives | 16 |
| False Positives | 2 |
| False Negatives | 4 |
| True Negatives | 18 |

**Git commit:** `6a1ab78` (`v0.4.0: Nous — Computational Reasoning Engine`)
**Model:** `claude-claude-sonnet-4-6` (entailment backend)
**Tasks:** 40 annotated tasks across 5 domains
**Mode:** `batch_mode=false`, `test_mode=false`

## Baseline Runs (for comparison)

| File | Notes |
|------|-------|
| `baseline_20260323_230835.json` | Keyword-matching baseline |
| `baseline_20260325_122818.json` | NLI embedding baseline |

## Earlier Runs (development history)

Files `run_20260319_*` through `run_20260324_*` are development-phase runs showing the improvement trajectory. The primary result is `run_20260325_121634.json`.

## Reproducing Table 1

```bash
bash scripts/reproduce_table1.sh
```

This runs the full evaluation pipeline and writes a new timestamped result file. See `scripts/reproduce_table1.sh` for exact environment requirements.

## Schema

Each JSON file has the following structure:

```json
{
  "timestamp": "YYYYMMDD_HHMMSS",
  "test_mode": false,
  "batch_mode": false,
  "eval_metrics": {
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0,
    "tp": 0, "fp": 0, "fn": 0, "tn": 0,
    "type_breakdown": { "ViolationType": { "detected": 0, "total": 0 } },
    "domain_breakdown": { "domain_name": { "precision": 0.0, "recall": 0.0, "f1": 0.0 } }
  },
  "task_results": [ ... ]
}
```
