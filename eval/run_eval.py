"""Nous Evaluation Runner.

Loads the evaluation dataset, runs the detector on each task,
compares results to ground truth, and outputs precision/recall/F1.

Features:
- Batch API mode for efficiency (~60 calls instead of ~335)
- Checkpoint after each task (resume on crash)
- Real-time progress with per-task timing
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nous.detector import detect_violations, detect_violations_batch, VIOLATION_TYPES
from nous.scorer import compute_metrics


def load_tasks(path: str | Path) -> list[dict]:
    """Load evaluation tasks from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_task(task: dict, test_mode: bool = True, use_batch: bool = False) -> dict:
    """Run detection on a single task and compare to ground truth.

    Returns a result dict with predicted/actual labels and details.
    """
    trace = task["trace"]
    ground_truth = task["ground_truth"]

    if use_batch and not test_mode:
        violations = detect_violations_batch(trace, test_mode=False)
    else:
        violations = detect_violations(trace, test_mode=test_mode)

    metrics = compute_metrics(violations, len(trace))

    predicted_has_violation = len(violations) > 0
    actual_has_violation = ground_truth["has_violation"]

    # Determine per-task PASS/FAIL
    correct = predicted_has_violation == actual_has_violation

    # Check violation type if applicable
    type_correct = True
    if actual_has_violation and predicted_has_violation:
        predicted_types = {v.violation_type for v in violations}
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
        "predicted_violations": [
            {
                "step_index": v.step_index,
                "violation_type": v.violation_type,
                "antecedent": v.antecedent,
                "entailed": v.entailed,
                "confidence": v.confidence,
            }
            for v in violations
        ],
        "ground_truth": ground_truth,
        "metrics": {
            "closure_score": metrics.closure_score,
            "violation_count": metrics.violation_count,
            "violation_breakdown": metrics.violation_breakdown,
        },
    }


def compute_eval_metrics(results: list[dict]) -> dict:
    """Compute precision, recall, F1 from task-level results."""
    tp = sum(1 for r in results if r["predicted_has_violation"] and r["actual_has_violation"])
    fp = sum(1 for r in results if r["predicted_has_violation"] and not r["actual_has_violation"])
    fn = sum(1 for r in results if not r["predicted_has_violation"] and r["actual_has_violation"])
    tn = sum(1 for r in results if not r["predicted_has_violation"] and not r["actual_has_violation"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Per-violation-type breakdown
    type_breakdown: dict[str, dict[str, int]] = {}
    for vtype in VIOLATION_TYPES:
        type_tp = sum(
            1 for r in results
            if r["actual_has_violation"]
            and r["ground_truth"].get("violation_type") == vtype
            and any(v["violation_type"] == vtype for v in r["predicted_violations"])
        )
        type_total = sum(
            1 for r in results
            if r["ground_truth"].get("violation_type") == vtype
        )
        type_breakdown[vtype] = {"detected": type_tp, "total": type_total}

    # Per-domain breakdown
    domains = set(r["domain"] for r in results)
    domain_breakdown: dict[str, dict[str, float]] = {}
    for domain in sorted(domains):
        domain_results = [r for r in results if r["domain"] == domain]
        d_tp = sum(1 for r in domain_results if r["predicted_has_violation"] and r["actual_has_violation"])
        d_fp = sum(1 for r in domain_results if r["predicted_has_violation"] and not r["actual_has_violation"])
        d_fn = sum(1 for r in domain_results if not r["predicted_has_violation"] and r["actual_has_violation"])
        d_prec = d_tp / (d_tp + d_fp) if (d_tp + d_fp) > 0 else 0.0
        d_rec = d_tp / (d_tp + d_fn) if (d_tp + d_fn) > 0 else 0.0
        d_f1 = 2 * d_prec * d_rec / (d_prec + d_rec) if (d_prec + d_rec) > 0 else 0.0
        domain_breakdown[domain] = {
            "precision": round(d_prec, 3),
            "recall": round(d_rec, 3),
            "f1": round(d_f1, 3),
            "tasks": len(domain_results),
        }

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "type_breakdown": type_breakdown,
        "domain_breakdown": domain_breakdown,
    }


def print_summary(results: list[dict], eval_metrics: dict) -> None:
    """Print a clean summary table to stdout."""
    print("\n" + "=" * 70)
    print("  Nous Evaluation Results")
    print("=" * 70)

    # Per-task results
    print(f"\n{'Task':<12} {'Domain':<18} {'Actual':<10} {'Predicted':<10} {'Result':<8}")
    print("-" * 60)
    for r in results:
        actual = "VIOL" if r["actual_has_violation"] else "CLEAN"
        predicted = "VIOL" if r["predicted_has_violation"] else "CLEAN"
        status = "PASS" if r["correct"] else "FAIL"
        print(f"{r['task_id']:<12} {r['domain']:<18} {actual:<10} {predicted:<10} {status:<8}")

    # Aggregate metrics
    m = eval_metrics
    print(f"\n{'-' * 40}")
    print(f"  Precision:  {m['precision']:.4f}")
    print(f"  Recall:     {m['recall']:.4f}")
    print(f"  F1 Score:   {m['f1']:.4f}")
    print(f"  TP={m['tp']}  FP={m['fp']}  FN={m['fn']}  TN={m['tn']}")

    # Violation type breakdown
    print(f"\n{'-' * 40}")
    print("  Per-Violation-Type Breakdown:")
    for vtype, counts in m["type_breakdown"].items():
        if counts["total"] > 0:
            print(f"    {vtype:<30} {counts['detected']}/{counts['total']}")

    # Domain breakdown
    print(f"\n{'-' * 40}")
    print("  Per-Domain Breakdown:")
    print(f"  {'Domain':<18} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Tasks':>6}")
    for domain, dm in m["domain_breakdown"].items():
        print(f"  {domain:<18} {dm['precision']:>6.3f} {dm['recall']:>6.3f} {dm['f1']:>6.3f} {dm['tasks']:>6}")

    print("\n" + "=" * 70)


def load_checkpoint(checkpoint_path: Path) -> list[dict]:
    """Load checkpoint results if they exist."""
    if checkpoint_path.is_file():
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("task_results", [])
    return []


def save_checkpoint(checkpoint_path: Path, results: list[dict], test_mode: bool) -> None:
    """Save checkpoint after each task."""
    data = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "test_mode": test_mode,
        "completed": len(results),
        "task_results": results,
    }
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main() -> None:
    """Run the full evaluation pipeline."""
    import argparse
    parser = argparse.ArgumentParser(description="Nous Evaluation")
    parser.add_argument("--test", action="store_true", help="Force test mode (fixtures only, no API)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint if available")
    args = parser.parse_args()

    dataset_path = Path(__file__).parent / "datasets" / "closure_tasks.json"
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    checkpoint_path = results_dir / "checkpoint.json"

    # Determine mode — no wasteful validation ping
    if args.test:
        test_mode = True
        print("[INFO] Test mode forced via --test flag.")
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            test_mode = False
            print("[INFO] API key found. Using Claude API with batch mode.")
        else:
            test_mode = True
            print("[INFO] No ANTHROPIC_API_KEY found. Running in test mode (hardcoded fixtures).")

    # Batch mode disabled — single calls are more reliable (batch hangs on large traces)
    use_batch = False

    # Load and evaluate
    tasks = load_tasks(dataset_path)
    print(f"[INFO] Loaded {len(tasks)} tasks from {dataset_path}")

    # Resume from checkpoint if requested
    results: list[dict] = []
    completed_ids: set[str] = set()
    if args.resume:
        results = load_checkpoint(checkpoint_path)
        completed_ids = {r["task_id"] for r in results}
        if completed_ids:
            print(f"[INFO] Resuming from checkpoint: {len(completed_ids)} tasks already complete.")

    skipped = 0
    total_time = 0.0
    remaining_tasks = [(i, t) for i, t in enumerate(tasks) if t["id"] not in completed_ids]

    for task_num, (i, task) in enumerate(remaining_tasks):
        label = "VIOL" if task["ground_truth"]["has_violation"] else "CLEAN"
        progress = len(completed_ids) + task_num + 1
        print(f"  [{progress}/{len(tasks)}] {task['id']} ({task['domain']}, {label})...", end=" ", flush=True)

        t0 = time.time()
        try:
            result = evaluate_task(task, test_mode=test_mode, use_batch=use_batch)
            elapsed = time.time() - t0
            total_time += elapsed
            status = "PASS" if result["correct"] else "FAIL"
            print(f"{status} ({elapsed:.1f}s)")
            results.append(result)

            # Checkpoint after each task
            if not test_mode:
                save_checkpoint(checkpoint_path, results, test_mode)
        except Exception as e:
            elapsed = time.time() - t0
            print(f"ERROR ({type(e).__name__}: {e}) ({elapsed:.1f}s)")
            skipped += 1

    if skipped:
        print(f"\n[WARN] {skipped} tasks skipped due to errors.")
    if total_time > 0:
        print(f"[INFO] Total inference time: {total_time:.1f}s ({total_time / max(1, len(remaining_tasks)):.1f}s/task avg)")

    # Compute metrics
    eval_metrics = compute_eval_metrics(results)

    # Print summary
    print_summary(results, eval_metrics)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = results_dir / f"run_{timestamp}.json"
    output = {
        "timestamp": timestamp,
        "test_mode": test_mode,
        "batch_mode": use_batch,
        "eval_metrics": eval_metrics,
        "task_results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n[INFO] Results saved to {output_path}")

    # Clean up checkpoint on successful completion
    if checkpoint_path.is_file() and not skipped:
        checkpoint_path.unlink()
        print("[INFO] Checkpoint cleaned up (all tasks complete).")


if __name__ == "__main__":
    main()
