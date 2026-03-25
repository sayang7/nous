#!/usr/bin/env python3
"""Re-test only the failed tasks from the last eval to check if prompt improvements fix them."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from closureguard.detector import detect_violations, CONFIDENCE_THRESHOLD, REVIEW_THRESHOLD

FAILED_TASK_IDS = ["task_007", "task_015", "task_017", "task_021", "task_028", "task_029"]

def main():
    with open(Path(__file__).parent / "datasets" / "closure_tasks.json") as f:
        all_tasks = json.load(f)

    tasks = [t for t in all_tasks if t["id"] in FAILED_TASK_IDS]

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    fixed = 0
    still_broken = 0

    for task in tasks:
        gt = task["ground_truth"]
        expected_viol = gt["has_violation"]
        expected_type = gt.get("violation_type")
        label = "FN" if expected_viol else "FP"

        print(f"\n{'='*60}")
        print(f"{task['id']} ({task['domain']}) — previously {label}")
        print(f"  Expected: {'VIOLATION (' + expected_type + ')' if expected_viol else 'CLEAN'}")

        violations = detect_violations(task["trace"], test_mode=False, api_key=key)
        predicted_viol = len(violations) > 0

        correct = predicted_viol == expected_viol

        if violations:
            for v in violations:
                review_tag = " [REVIEW]" if v.needs_review else ""
                print(f"  Detected: {v.violation_type} at step {v.step_index} (conf={v.confidence:.2f}){review_tag}")
                print(f"    Commitment: {v.antecedent[:80]}")
        else:
            print(f"  Detected: CLEAN")

        if correct:
            print(f"  => FIXED!")
            fixed += 1
        else:
            print(f"  => STILL BROKEN")
            still_broken += 1

    print(f"\n{'='*60}")
    print(f"Results: {fixed}/6 fixed, {still_broken}/6 still broken")


if __name__ == "__main__":
    main()
