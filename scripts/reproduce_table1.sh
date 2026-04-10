#!/usr/bin/env bash
# reproduce_table1.sh — Reproduce the primary benchmark result (Table 1 in the paper)
#
# Usage:
#   export ANTHROPIC_API_KEY=your_key_here
#   bash scripts/reproduce_table1.sh
#
# Output: eval/results/reproduction-<timestamp>.json
# Expected: precision ≈ 0.889, recall ≈ 0.800, F1 ≈ 0.842

set -euo pipefail

# ── environment check ────────────────────────────────────────────────────────
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set."
  echo "  export ANTHROPIC_API_KEY=your_key_here"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$REPO_ROOT/eval/results"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT="$RESULTS_DIR/reproduction-$TIMESTAMP.json"

cd "$REPO_ROOT"

# ── dependency check ─────────────────────────────────────────────────────────
echo "=== Nous — Table 1 Reproduction ==="
echo "Checking dependencies..."
pip install -q -r requirements-lock.txt

# ── run evaluation ───────────────────────────────────────────────────────────
echo "Running evaluation (40 tasks, ~5 minutes with API)..."
python eval/run_eval.py \
  --output "$OUTPUT" \
  --tasks eval/datasets/closure_tasks.json

# ── print summary ─────────────────────────────────────────────────────────────
echo ""
echo "Results written to: $OUTPUT"
echo ""
python -c "
import json, sys
with open('$OUTPUT') as f:
    d = json.load(f)
m = d['eval_metrics']
print(f'  Precision : {m[\"precision\"]:.3f}  (paper: 0.889)')
print(f'  Recall    : {m[\"recall\"]:.3f}  (paper: 0.800)')
print(f'  F1        : {m[\"f1\"]:.3f}  (paper: 0.842)')
print(f'  TP/FP/FN/TN: {m[\"tp\"]}/{m[\"fp\"]}/{m[\"fn\"]}/{m[\"tn\"]}')
delta_f1 = abs(m['f1'] - 0.842)
if delta_f1 < 0.02:
    print(f'  ✓ Result matches paper within tolerance (Δ={delta_f1:.3f})')
else:
    print(f'  ⚠ Result differs from paper by {delta_f1:.3f} — check model version')
"
