"""ClosureGuard Evaluation Runner.

Loads the evaluation dataset, runs the detector on each task,
compares results to ground truth, and outputs precision/recall/F1.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from closureguard.detector import detect_violations, VIOLATION_TYPES
from closureguard.scorer import compute_metrics


def load_tasks(path: str | Path) -> list[dict]:
    """Load evaluation tasks from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_task(task: dict, test_mode: bool = True) -> dict:
    """Run detection on a single task and compare to ground truth.

    Returns a result dict with predicted/actual labels and details.
    """
    trace = task["trace"]
    ground_truth = task["ground_truth"]

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
    print("  ClosureGuard Evaluation Results")
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


def main() -> None:
    """Run the full evaluation pipeline."""
    import argparse
    parser = argparse.ArgumentParser(description="ClosureGuard Evaluation")
    parser.add_argument("--test", action="store_true", help="Force test mode (fixtures only, no API)")
    args = parser.parse_args()

    dataset_path = Path(__file__).parent / "datasets" / "closure_tasks.json"
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    # Determine mode
    if args.test:
        test_mode = True
        print("[INFO] Test mode forced via --test flag.")
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        test_mode = True
        if api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Say OK"}],
                )
                test_mode = False
                print("[INFO] API key validated. Using Claude API for inference.")
            except Exception as e:
                print(f"[WARN] API key invalid ({type(e).__name__}). Falling back to test mode.")
                test_mode = True
        else:
            print("[INFO] No ANTHROPIC_API_KEY found. Running in test mode (hardcoded fixtures).")

    # Load and evaluate
    tasks = load_tasks(dataset_path)
    print(f"[INFO] Loaded {len(tasks)} tasks from {dataset_path}")

    results = []
    skipped = 0
    for i, task in enumerate(tasks):
        label = "VIOL" if task["ground_truth"]["has_violation"] else "CLEAN"
        print(f"  [{i+1}/{len(tasks)}] {task['id']} ({task['domain']}, {label})...", end=" ", flush=True)
        try:
            result = evaluate_task(task, test_mode=test_mode)
            status = "PASS" if result["correct"] else "FAIL"
            print(status)
            results.append(result)
        except Exception as e:
            print(f"ERROR ({type(e).__name__})")
            skipped += 1
    if skipped:
        print(f"\n[WARN] {skipped} tasks skipped due to errors.")

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
        "eval_metrics": eval_metrics,
        "task_results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n[INFO] Results saved to {output_path}")


if __name__ == "__main__":
    main()
