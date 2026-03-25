"""Baseline evaluation: single-prompt vs decomposed pipeline.

Runs the naive baseline (send whole trace to Claude) on the same benchmark,
then compares to the pipeline results. This proves whether the decomposed
architecture (extractor -> checker -> detector) adds value.

Usage:
    python -u eval/run_baseline.py
    python -u eval/run_baseline.py --compare eval/results/run_XXXXXXXX_XXXXXX.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from closureguard.baseline import baseline_detect
from closureguard.detector import VIOLATION_TYPES


def load_tasks(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_task_baseline(task: dict) -> dict:
    """Run baseline on a single task."""
    trace = task["trace"]
    ground_truth = task["ground_truth"]

    result = baseline_detect(trace)
    predicted_has_violation = len(result.violations) > 0
    actual_has_violation = ground_truth["has_violation"]
    correct = predicted_has_violation == actual_has_violation

    type_correct = True
    if actual_has_violation and predicted_has_violation:
        predicted_types = {v.get("violation_type") for v in result.violations}
        expected_type = ground_truth.get("violation_type")
        if expected_type:
            type_correct = expected_type in predicted_types

    return {
        "task_id": task["id"],
        "domain": task["domain"],
        "predicted_has_violation": predicted_has_violation,
        "actual_has_violation": actual_has_violation,
        "correct": correct,
        "type_correct": type_correct if actual_has_violation else None,
        "predicted_violations": result.violations,
        "ground_truth": ground_truth,
    }


def compute_metrics(results: list[dict]) -> dict:
    tp = sum(1 for r in results if r["predicted_has_violation"] and r["actual_has_violation"])
    fp = sum(1 for r in results if r["predicted_has_violation"] and not r["actual_has_violation"])
    fn = sum(1 for r in results if not r["predicted_has_violation"] and r["actual_has_violation"])
    tn = sum(1 for r in results if not r["predicted_has_violation"] and not r["actual_has_violation"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    type_breakdown: dict[str, dict[str, int]] = {}
    for vtype in VIOLATION_TYPES:
        type_tp = sum(
            1 for r in results
            if r["actual_has_violation"]
            and r["ground_truth"].get("violation_type") == vtype
            and any(v.get("violation_type") == vtype for v in r["predicted_violations"])
        )
        type_total = sum(
            1 for r in results
            if r["ground_truth"].get("violation_type") == vtype
        )
        type_breakdown[vtype] = {"detected": type_tp, "total": type_total}

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "type_breakdown": type_breakdown,
    }


def print_comparison(baseline_metrics: dict, pipeline_metrics: dict | None) -> None:
    print("\n" + "=" * 70)
    print("  Baseline vs Pipeline Comparison")
    print("=" * 70)

    headers = f"{'Metric':<20}"
    baseline_col = f"{'Baseline':>12}"
    pipeline_col = f"{'Pipeline':>12}" if pipeline_metrics else ""
    delta_col = f"{'Delta':>12}" if pipeline_metrics else ""
    print(f"\n{headers}{baseline_col}{pipeline_col}{delta_col}")
    print("-" * (20 + 12 + (24 if pipeline_metrics else 0)))

    bm = baseline_metrics
    for metric in ["precision", "recall", "f1"]:
        bval = bm[metric]
        line = f"  {metric.capitalize():<18}{bval:>12.4f}"
        if pipeline_metrics:
            pval = pipeline_metrics[metric]
            delta = pval - bval
            sign = "+" if delta > 0 else ""
            line += f"{pval:>12.4f}{sign}{delta:>11.4f}"
        print(line)

    line = f"  {'TP/FP/FN/TN':<18}{bm['tp']}/{bm['fp']}/{bm['fn']}/{bm['tn']:>8}"
    if pipeline_metrics:
        pm = pipeline_metrics
        line += f"   {pm['tp']}/{pm['fp']}/{pm['fn']}/{pm['tn']:>8}"
    print(line)

    # Type breakdown comparison
    print(f"\n  Per-Type Detection:")
    for vtype in VIOLATION_TYPES:
        bc = bm["type_breakdown"].get(vtype, {"detected": 0, "total": 0})
        if bc["total"] > 0:
            line = f"    {vtype:<30} {bc['detected']}/{bc['total']}"
            if pipeline_metrics:
                pc = pipeline_metrics["type_breakdown"].get(vtype, {"detected": 0, "total": 0})
                line += f"  vs  {pc['detected']}/{pc['total']}"
            print(line)

    print("\n" + "=" * 70)
    if pipeline_metrics:
        bf1 = bm["f1"]
        pf1 = pipeline_metrics["f1"]
        if pf1 > bf1:
            print(f"  Pipeline outperforms baseline by {pf1 - bf1:+.4f} F1")
        elif pf1 < bf1:
            print(f"  WARNING: Baseline outperforms pipeline by {bf1 - pf1:+.4f} F1")
            print(f"  The decomposed architecture may not be justified.")
        else:
            print(f"  Pipeline and baseline perform identically.")
    print("=" * 70)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="ClosureGuard Baseline Evaluation")
    parser.add_argument("--compare", type=str, help="Path to pipeline eval results JSON for comparison")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY required for baseline evaluation.")
        sys.exit(1)

    dataset_path = Path(__file__).parent / "datasets" / "closure_tasks.json"
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    tasks = load_tasks(dataset_path)
    print(f"[INFO] Loaded {len(tasks)} tasks. Running naive baseline...")

    results: list[dict] = []
    skipped = 0
    total_time = 0.0

    for i, task in enumerate(tasks):
        label = "VIOL" if task["ground_truth"]["has_violation"] else "CLEAN"
        print(f"  [{i+1}/{len(tasks)}] {task['id']} ({task['domain']}, {label})...", end=" ", flush=True)

        t0 = time.time()
        try:
            result = evaluate_task_baseline(task)
            elapsed = time.time() - t0
            total_time += elapsed
            status = "PASS" if result["correct"] else "FAIL"
            print(f"{status} ({elapsed:.1f}s)")
            results.append(result)
        except Exception as e:
            elapsed = time.time() - t0
            print(f"ERROR ({type(e).__name__}: {e}) ({elapsed:.1f}s)")
            skipped += 1

    if skipped:
        print(f"\n[WARN] {skipped} tasks skipped due to errors.")
    print(f"[INFO] Total time: {total_time:.1f}s ({total_time / max(1, len(tasks)):.1f}s/task avg)")

    baseline_metrics = compute_metrics(results)

    # Load pipeline results for comparison
    pipeline_metrics = None
    if args.compare:
        try:
            with open(args.compare, "r") as f:
                pipeline_data = json.load(f)
            pipeline_metrics = pipeline_data.get("eval_metrics")
            print(f"[INFO] Loaded pipeline results from {args.compare}")
        except Exception as e:
            print(f"[WARN] Could not load pipeline results: {e}")

    print_comparison(baseline_metrics, pipeline_metrics)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = results_dir / f"baseline_{timestamp}.json"
    output = {
        "timestamp": timestamp,
        "method": "naive_baseline",
        "eval_metrics": baseline_metrics,
        "task_results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n[INFO] Baseline results saved to {output_path}")


if __name__ == "__main__":
    main()
