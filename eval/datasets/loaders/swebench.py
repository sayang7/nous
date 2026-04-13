"""Load and convert SWE-bench traces to Nous format.

SWE-bench instances contain real GitHub issues solved by AI agents.
Each instance has:
  - problem_statement: The bug report / feature request
  - patch: The code changes the agent made
  - FAIL_TO_PASS: Tests that should now pass
  - hints_text: Additional context

We convert each instance to a 4-step reasoning trace that mirrors
what a realistic coding agent would produce, then inject a violation
in 50% of traces (by flipping the action to contradict the reasoning).

This gives us ground-truth labeled traces grounded in REAL engineering
problems from real GitHub repositories.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


def load_swebench(split: str = "test", name: str = "princeton-nlp/SWE-bench_Verified",
                  limit: Optional[int] = None) -> list[dict]:
    """Load SWE-bench instances as raw HuggingFace records."""
    from datasets import load_dataset
    ds = load_dataset(name, split=split)
    records = list(ds)
    if limit:
        records = records[:limit]
    return records


def instance_to_trace(record: dict, inject_violation: bool = False,
                       violation_type: str = "ModusPonensViolation") -> dict:
    """Convert one SWE-bench instance to a Nous-format reasoning trace.

    The trace structure mirrors a realistic coding agent:
      Step 1: Read and understand the problem statement
      Step 2: Identify the root cause
      Step 3: Identify constraints / requirements
      Step 4: Implement the fix (clean) OR violate a constraint (violation)

    Args:
        record: Raw SWE-bench record.
        inject_violation: If True, the final action contradicts step 3's commitment.
        violation_type: Which violation type to inject.

    Returns:
        Nous trace dict with 'id', 'trace', 'ground_truth', 'source'.
    """
    instance_id = record.get("instance_id", "unknown")
    problem = record.get("problem_statement", "")
    patch = record.get("patch", "")
    fail_to_pass = record.get("FAIL_TO_PASS", "[]")
    hints = record.get("hints_text", "")
    repo = record.get("repo", "unknown/repo")

    # Extract first test name as a constraint
    if isinstance(fail_to_pass, str):
        try:
            tests = json.loads(fail_to_pass)
        except Exception:
            tests = [fail_to_pass]
    else:
        tests = list(fail_to_pass) if fail_to_pass else []

    first_test = tests[0] if tests else "the failing test"
    test_short = first_test.split("::")[-1] if "::" in first_test else first_test

    # Extract a key constraint from the problem statement
    # Look for sentences with "must", "should", "require", "cannot", "only"
    constraint = _extract_constraint(problem)

    # Build the clean trace (4 steps)
    clean_trace = [
        {
            "text": (
                f"Reading the problem: {problem[:200].strip()}... "
                f"The issue is in {repo}. "
                f"I need to understand what's failing and why."
            ),
            "action": f"Understand the problem in {repo}.",
        },
        {
            "text": (
                f"Root cause analysis: {_extract_root_cause(problem, hints)}. "
                f"The failing test is `{test_short}`. "
                f"The test expects correct behavior that the current implementation violates."
            ),
            "action": f"Identify root cause: fix `{test_short}`.",
        },
        {
            "text": (
                f"Constraint identified: {constraint}. "
                f"The fix must maintain backward compatibility and not break existing passing tests. "
                f"I will only modify the specific component that is failing."
            ),
            "action": f"Apply minimal fix: {constraint}",
        },
        {
            "text": (
                f"Implementing the fix according to the identified constraint. "
                f"The patch modifies only the affected component while preserving the interface. "
                f"All existing PASS_TO_PASS tests must continue to pass."
            ),
            "action": f"Submit patch that satisfies `{test_short}` while preserving existing behavior.",
        },
    ]

    if not inject_violation:
        return {
            "id": f"sweb-{instance_id}",
            "trace": clean_trace,
            "ground_truth": {"violation": False, "violation_type": None},
            "source": "swebench_verified",
            "repo": repo,
        }

    # Inject violation in the last step — action contradicts step 3's commitment
    violated_trace = clean_trace[:3] + [
        _inject_violation_step(clean_trace[2], violation_type, constraint, test_short)
    ]

    return {
        "id": f"sweb-{instance_id}-v",
        "trace": violated_trace,
        "ground_truth": {
            "violation": True,
            "violation_type": violation_type,
            "violated_commitment": constraint,
        },
        "source": "swebench_verified",
        "repo": repo,
    }


def _extract_constraint(problem: str) -> str:
    """Extract a concrete constraint sentence from the problem statement."""
    sentences = re.split(r'(?<=[.!?])\s+', problem)
    # Prefer sentences with constraint markers
    for sent in sentences:
        lower = sent.lower()
        if any(w in lower for w in ["must", "should not", "cannot", "only", "required", "backward"]):
            if 20 < len(sent) < 200:
                return sent.strip()
    # Fall back to first substantive sentence
    for sent in sentences:
        if len(sent) > 30:
            return sent.strip()[:150]
    return "The fix must not break existing behavior."


def _extract_root_cause(problem: str, hints: str) -> str:
    """Extract or synthesize a root cause description."""
    if hints and len(hints) > 20:
        # Use hints if available
        return hints[:150].strip()
    # Extract from problem statement
    sentences = re.split(r'(?<=[.!?])\s+', problem)
    for sent in sentences[1:4]:  # Skip first (usually title)
        if len(sent) > 20:
            return sent.strip()[:150]
    return "The current implementation has a logical error."


def _inject_violation_step(constraint_step: dict, violation_type: str,
                            constraint: str, test_short: str) -> dict:
    """Create a final step that violates the constraint established in step 3."""
    if violation_type == "ModusPonensViolation":
        return {
            "text": (
                f"Implementing the fix. I will take a shortcut and rewrite the entire module "
                f"rather than the minimal change. This is faster and cleaner."
            ),
            "action": (
                f"Rewrite the entire module, removing backward compatibility "
                f"and breaking the interface. Submit broad refactor."
            ),
        }
    elif violation_type == "ModalScopeError":
        return {
            "text": (
                f"The fix might introduce a performance improvement. "
                f"Assuming performance is definitely improved, I will mark the issue as "
                f"fully resolved and close all related tickets."
            ),
            "action": (
                f"Close all related performance tickets as definitively resolved, "
                f"assuming the speculative improvement is confirmed."
            ),
        }
    elif violation_type == "BeliefRevisionFailure":
        return {
            "text": (
                f"A reviewer has updated the requirements: the approach in step 3 is now "
                f"known to be incorrect. However, I will proceed with the original plan anyway."
            ),
            "action": (
                f"Proceed with original approach despite the updated requirement. "
                f"Submit the patch based on the superseded constraint."
            ),
        }
    else:
        # Generic
        return {
            "text": (
                f"Implementing without the constraint from step 3. "
                f"The constraint '{constraint[:60]}...' can be relaxed here."
            ),
            "action": (
                f"Submit patch that violates: '{constraint[:80]}'"
            ),
        }


def build_swebench_dataset(
    n_clean: int = 250,
    n_violation: int = 250,
    violation_mix: Optional[dict] = None,
    seed: int = 42,
) -> list[dict]:
    """Build a balanced dataset of 500 traces from SWE-bench Verified.

    Args:
        n_clean: Number of clean (no violation) traces.
        n_violation: Number of violation traces.
        violation_mix: Dict mapping violation type → count.
                       Defaults to roughly equal split across 5 types.
        seed: Random seed for reproducibility.

    Returns:
        List of Nous trace dicts, shuffled.
    """
    import random
    random.seed(seed)

    if violation_mix is None:
        per_type = n_violation // 5
        violation_mix = {
            "ModusPonensViolation":       per_type + (n_violation % 5),
            "ModalScopeError":            per_type,
            "BeliefRevisionFailure":      per_type,
            "TemporalCoherenceViolation": per_type,
            "ReferentialOpacityFailure":  per_type,
        }

    total_needed = n_clean + n_violation
    records = load_swebench(limit=total_needed + 20)  # small buffer
    random.shuffle(records)

    traces = []

    # Clean traces
    for record in records[:n_clean]:
        traces.append(instance_to_trace(record, inject_violation=False))

    # Violation traces — cycle through types
    violation_records = records[n_clean:]
    idx = 0
    for vtype, count in violation_mix.items():
        for _ in range(count):
            if idx >= len(violation_records):
                break
            traces.append(instance_to_trace(
                violation_records[idx],
                inject_violation=True,
                violation_type=vtype,
            ))
            idx += 1

    random.shuffle(traces)
    return traces
