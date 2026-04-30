"""Tests for the legacy detection pipeline.

These test the detector.py/scorer.py/baseline.py modules used by the
evaluation benchmark. All tests use test_mode=True (fixtures, no API).

For tests of the primary Nous API, see test_nous.py.
"""

import pytest

from nous.extractor import extract_beliefs, extract_beliefs_batch
from nous.detector import (
    detect_violations,
    detect_violations_batch,
    closure_score,
    ClosureViolationReport,
    VIOLATION_TYPES,
)


# ─── Extractor Tests ─────────────────────────────────────────────

class TestExtractor:
    def test_extracts_beliefs_from_known_text(self):
        beliefs = extract_beliefs(
            "The API documentation confirms the endpoint returns JSON.",
            test_mode=True,
        )
        assert len(beliefs) >= 1
        assert any("JSON" in b for b in beliefs)

    def test_returns_empty_for_unknown_text(self):
        beliefs = extract_beliefs(
            "Something completely unrelated to any fixture.",
            test_mode=True,
        )
        assert beliefs == []

    def test_multiple_beliefs_from_single_step(self):
        beliefs = extract_beliefs(
            "The system reports config.yaml was deleted in the last deployment.",
            test_mode=True,
        )
        assert len(beliefs) >= 2

    def test_returns_list_of_strings(self):
        beliefs = extract_beliefs(
            "The input n = 42 is an even number.",
            test_mode=True,
        )
        assert isinstance(beliefs, list)
        assert all(isinstance(b, str) for b in beliefs)


# ─── Detector Tests ───────────────────────────────────────────────

class TestDetector:
    def test_detects_modus_ponens_violation(self):
        trace = [
            {"step": 1, "text": "The API documentation confirms the endpoint returns JSON.",
             "action": "Send GET request to the endpoint."},
            {"step": 2, "text": "JSON responses need to be parsed before accessing fields.",
             "action": "Store the response body."},
            {"step": 3, "text": "Let me extract the 'name' field from the response.",
             "action": "Split response string by commas to find name."},
        ]
        violations = detect_violations(trace, test_mode=True)
        assert len(violations) >= 1
        assert any(v.violation_type == "ModusPonensViolation" for v in violations)

    def test_detects_belief_revision_failure(self):
        trace = [
            {"step": 1, "text": "I'll read the configuration from config.yaml.",
             "action": "Open config.yaml for reading."},
            {"step": 2, "text": "The system reports config.yaml was deleted in the last deployment.",
             "action": "Acknowledge file deletion."},
            {"step": 3, "text": "Now let me parse the database URL from config.yaml.",
             "action": "Read database_url field from config.yaml."},
        ]
        violations = detect_violations(trace, test_mode=True)
        assert len(violations) >= 1
        assert any(v.violation_type == "BeliefRevisionFailure" for v in violations)

    def test_detects_temporal_coherence_violation(self):
        trace = [
            {"step": 1, "text": "Health check at 14:00 shows the database server is unreachable.",
             "action": "Log server as unreachable."},
            {"step": 2, "text": "I need to fetch user records to complete this task.",
             "action": "Query the database server for user records."},
            {"step": 3, "text": "Let me process the query results.",
             "action": "Iterate over returned user records."},
        ]
        violations = detect_violations(trace, test_mode=True)
        assert len(violations) >= 1
        assert any(v.violation_type == "TemporalCoherenceViolation" for v in violations)

    def test_coherent_trace_has_no_violations(self):
        trace = [
            {"step": 1, "text": "The input n = 42 is an even number.",
             "action": "Store n = 42 as even."},
            {"step": 2, "text": "Since n is even, n is divisible by 2.",
             "action": "Compute n / 2 = 21."},
            {"step": 3, "text": "The result is 21.",
             "action": "Return 21."},
        ]
        violations = detect_violations(trace, test_mode=True)
        assert len(violations) == 0

    def test_violation_report_has_required_fields(self):
        trace = [
            {"step": 1, "text": "The API documentation confirms the endpoint returns JSON.",
             "action": "Send GET request."},
            {"step": 2, "text": "JSON responses need to be parsed before accessing fields.",
             "action": "Store response."},
            {"step": 3, "text": "Let me extract the 'name' field from the response.",
             "action": "Split response string by commas to find name."},
        ]
        violations = detect_violations(trace, test_mode=True)
        assert len(violations) >= 1
        v = violations[0]
        assert isinstance(v.step_index, int)
        assert isinstance(v.antecedent, str)
        assert isinstance(v.entailed, str)
        assert isinstance(v.action, str)
        assert v.violation_type in VIOLATION_TYPES
        assert 0.0 <= v.confidence <= 1.0

    def test_violation_types_match_lean_taxonomy(self):
        expected = {
            "ModusPonensViolation",
            "BeliefRevisionFailure",
            "ModalScopeError",
            "TemporalCoherenceViolation",
            "ReferentialOpacityFailure",
        }
        assert set(VIOLATION_TYPES) == expected

    def test_api_auth_error_propagates(self):
        trace = [
            {"step": 1, "text": "Some belief.", "action": "Some action."},
        ]
        with pytest.raises(RuntimeError, match="authentication failed"):
            detect_violations(trace, test_mode=False, api_key="sk-invalid-key")


# ─── Closure Score Tests ──────────────────────────────────────────

class TestClosureScore:
    def test_zero_violations(self):
        assert closure_score([], 5) == 0.0

    def test_bounded_at_one(self):
        violations = [
            ClosureViolationReport(
                step_index=i, antecedent="a", entailed="b",
                action="c", violation_type="ModusPonensViolation",
                confidence=0.9,
            )
            for i in range(10)
        ]
        assert closure_score(violations, 3) == 1.0

    def test_zero_steps(self):
        assert closure_score([], 0) == 0.0

    def test_correct_ratio(self):
        violations = [
            ClosureViolationReport(
                step_index=1, antecedent="a", entailed="b",
                action="c", violation_type="ModusPonensViolation",
                confidence=0.9,
            )
        ]
        assert closure_score(violations, 4) == 0.25


# ─── Batch Equivalence Tests ─────────────────────────────────────

class TestBatchExtractor:
    def test_batch_matches_single(self):
        steps = [
            "The API documentation confirms the endpoint returns JSON.",
            "The system reports config.yaml was deleted in the last deployment.",
            "The input n = 42 is an even number.",
        ]
        single_results = [extract_beliefs(s, test_mode=True) for s in steps]
        batch_results = extract_beliefs_batch(steps, test_mode=True)
        assert single_results == batch_results

    def test_batch_empty_input(self):
        assert extract_beliefs_batch([], test_mode=True) == []

    def test_batch_unknown_text(self):
        results = extract_beliefs_batch(["Unknown text xyz."], test_mode=True)
        assert results == [[]]


class TestBatchDetector:
    def test_batch_matches_single_modus_ponens(self):
        trace = [
            {"step": 1, "text": "The API documentation confirms the endpoint returns JSON.",
             "action": "Send GET request to the endpoint."},
            {"step": 2, "text": "JSON responses need to be parsed before accessing fields.",
             "action": "Store the response body."},
            {"step": 3, "text": "Let me extract the 'name' field from the response.",
             "action": "Split response string by commas to find name."},
        ]
        single = detect_violations(trace, test_mode=True)
        batch = detect_violations_batch(trace, test_mode=True)

        assert len(single) == len(batch)
        for s, b in zip(single, batch):
            assert s.step_index == b.step_index
            assert s.violation_type == b.violation_type

    def test_batch_coherent_trace(self):
        trace = [
            {"step": 1, "text": "The input n = 42 is an even number.",
             "action": "Store n = 42 as even."},
            {"step": 2, "text": "Since n is even, n is divisible by 2.",
             "action": "Compute n / 2 = 21."},
            {"step": 3, "text": "The result is 21.",
             "action": "Return 21."},
        ]
        violations = detect_violations_batch(trace, test_mode=True)
        assert len(violations) == 0

    def test_batch_empty_trace(self):
        assert detect_violations_batch([], test_mode=True) == []

    def test_batch_belief_revision_failure(self):
        trace = [
            {"step": 1, "text": "I'll read the configuration from config.yaml.",
             "action": "Open config.yaml for reading."},
            {"step": 2, "text": "The system reports config.yaml was deleted in the last deployment.",
             "action": "Acknowledge file deletion."},
            {"step": 3, "text": "Now let me parse the database URL from config.yaml.",
             "action": "Read database_url field from config.yaml."},
        ]
        violations = detect_violations_batch(trace, test_mode=True)
        assert len(violations) >= 1
        assert any(v.violation_type == "BeliefRevisionFailure" for v in violations)
