"""Tests for the ClosureGuard detection pipeline.

All tests use test_mode=True (hardcoded fixtures, no API calls).
"""

import pytest

from closureguard.extractor import extract_beliefs, extract_beliefs_batch
from closureguard.checker import check_entailment, check_entailment_batch, clear_cache, EntailmentResult
from closureguard.detector import (
    detect_violations,
    detect_violations_batch,
    closure_score,
    ClosureViolationReport,
    VIOLATION_TYPES,
)
from closureguard.scorer import compute_metrics


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


# ─── Checker Tests ────────────────────────────────────────────────

class TestChecker:
    def setup_method(self):
        clear_cache()

    def test_positive_entailment(self):
        result = check_entailment(
            "The API endpoint returns JSON.",
            "The response must be parsed as JSON to extract fields.",
            test_mode=True,
        )
        assert result.entails is True
        assert result.confidence > 0.8
        assert result.violation_type is None

    def test_violation_detected(self):
        result = check_entailment(
            "The API endpoint returns JSON.",
            "Split response string by commas to find name.",
            test_mode=True,
        )
        assert result.entails is False
        assert result.violation_type == "ModusPonensViolation"
        assert result.explanation is not None
        assert result.confidence > 0.8

    def test_cache_returns_same_result(self):
        r1 = check_entailment("The API endpoint returns JSON.",
                               "The response must be parsed as JSON to extract fields.",
                               test_mode=True)
        r2 = check_entailment("The API endpoint returns JSON.",
                               "The response must be parsed as JSON to extract fields.",
                               test_mode=True)
        assert r1 == r2

    def test_unknown_pair_defaults_to_coherent(self):
        """Unknown pairs should be treated as coherent (no false positives)."""
        result = check_entailment(
            "The sky is blue.",
            "Water is wet.",
            test_mode=True,
        )
        assert result.entails is True
        assert result.violation_type is None

    def test_confidence_is_bounded(self):
        result = check_entailment(
            "The number 42 is even.",
            "42 is divisible by 2.",
            test_mode=True,
        )
        assert 0.0 <= result.confidence <= 1.0

    def test_violation_type_in_taxonomy(self):
        result = check_entailment(
            "config.yaml was deleted in the last deployment.",
            "Read database_url field from config.yaml.",
            test_mode=True,
        )
        assert result.violation_type in VIOLATION_TYPES


# ─── Detector Tests ───────────────────────────────────────────────

class TestDetector:
    def test_detects_modus_ponens_violation(self):
        """Agent states API returns JSON, says JSON must be parsed,
        then string-splits the response."""
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
        """Agent learns file was deleted, then reads from it."""
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
        """Agent notes server is down, then queries it."""
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
        """Coherent math reasoning should produce no violations."""
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
        """All violation types in Python must match the Lean taxonomy."""
        expected = {
            "ModusPonensViolation",
            "BeliefRevisionFailure",
            "ModalScopeError",
            "TemporalCoherenceViolation",
            "ReferentialOpacityFailure",
        }
        assert set(VIOLATION_TYPES) == expected

    def test_api_auth_error_propagates(self):
        """Auth errors should raise RuntimeError, not silently return empty."""
        trace = [
            {"step": 1, "text": "Some belief.", "action": "Some action."},
        ]
        # With an explicitly invalid key, should raise RuntimeError
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


# ─── Scorer Tests ─────────────────────────────────────────────────

class TestScorer:
    def test_metrics_from_violations(self):
        violations = [
            ClosureViolationReport(
                step_index=1, antecedent="a", entailed="b",
                action="c", violation_type="ModusPonensViolation",
                confidence=0.9,
            ),
            ClosureViolationReport(
                step_index=2, antecedent="d", entailed="e",
                action="f", violation_type="BeliefRevisionFailure",
                confidence=0.85,
            ),
        ]
        metrics = compute_metrics(violations, 5)
        assert metrics.closure_score == pytest.approx(0.4)
        assert metrics.violation_count == 2
        assert metrics.steps_analyzed == 5
        assert "ModusPonensViolation" in metrics.violation_breakdown
        assert "BeliefRevisionFailure" in metrics.violation_breakdown
        assert metrics.most_common_violation in VIOLATION_TYPES

    def test_no_violations_metrics(self):
        metrics = compute_metrics([], 3)
        assert metrics.closure_score == 0.0
        assert metrics.violation_count == 0
        assert metrics.most_common_violation == "None"

    def test_zero_steps_metrics(self):
        metrics = compute_metrics([], 0)
        assert metrics.steps_analyzed == 0
        assert metrics.closure_score == 0.0


# ─── Batch Equivalence Tests ─────────────────────────────────────

class TestBatchExtractor:
    def test_batch_matches_single(self):
        """Batch extraction should return same results as single calls."""
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


class TestBatchChecker:
    def setup_method(self):
        clear_cache()

    def test_batch_matches_single(self):
        """Batch checking should return same results as single calls."""
        pairs = [
            ("The API endpoint returns JSON.", "The response must be parsed as JSON to extract fields."),
            ("The API endpoint returns JSON.", "Split response string by commas to find name."),
            ("The number 42 is even.", "42 is divisible by 2."),
        ]
        single_results = []
        for a, b in pairs:
            clear_cache()
            single_results.append(check_entailment(a, b, test_mode=True))
        clear_cache()
        batch_results = check_entailment_batch(pairs, test_mode=True)

        for single, batch in zip(single_results, batch_results):
            assert single.entails == batch.entails
            assert single.violation_type == batch.violation_type
            assert single.confidence == batch.confidence

    def test_batch_empty_input(self):
        assert check_entailment_batch([], test_mode=True) == []

    def test_batch_caching(self):
        """Batch should populate cache; second call uses cache."""
        clear_cache()
        pairs = [("The number 42 is even.", "42 is divisible by 2.")]
        r1 = check_entailment_batch(pairs, test_mode=True)
        r2 = check_entailment_batch(pairs, test_mode=True)
        assert r1[0].entails == r2[0].entails


class TestBatchDetector:
    def test_batch_matches_single_modus_ponens(self):
        """Batch detector should find same violations as single detector."""
        trace = [
            {"step": 1, "text": "The API documentation confirms the endpoint returns JSON.",
             "action": "Send GET request to the endpoint."},
            {"step": 2, "text": "JSON responses need to be parsed before accessing fields.",
             "action": "Store the response body."},
            {"step": 3, "text": "Let me extract the 'name' field from the response.",
             "action": "Split response string by commas to find name."},
        ]
        clear_cache()
        single = detect_violations(trace, test_mode=True)
        clear_cache()
        batch = detect_violations_batch(trace, test_mode=True)

        assert len(single) == len(batch)
        for s, b in zip(single, batch):
            assert s.step_index == b.step_index
            assert s.violation_type == b.violation_type
            assert s.antecedent == b.antecedent

    def test_batch_coherent_trace(self):
        """Batch detector on coherent trace should find no violations."""
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
        """Batch detector should find BeliefRevisionFailure."""
        trace = [
            {"step": 1, "text": "I'll read the configuration from config.yaml.",
             "action": "Open config.yaml for reading."},
            {"step": 2, "text": "The system reports config.yaml was deleted in the last deployment.",
             "action": "Acknowledge file deletion."},
            {"step": 3, "text": "Now let me parse the database URL from config.yaml.",
             "action": "Read database_url field from config.yaml."},
        ]
        clear_cache()
        violations = detect_violations_batch(trace, test_mode=True)
        assert len(violations) >= 1
        assert any(v.violation_type == "BeliefRevisionFailure" for v in violations)


# ─── Baseline Module Tests ──────────────────────────────────────

class TestBaseline:
    def test_baseline_module_imports(self):
        """Baseline module should be importable."""
        from closureguard.baseline import baseline_detect, BaselineResult, BASELINE_PROMPT
        assert callable(baseline_detect)
        assert "{trace_text}" in BASELINE_PROMPT

    def test_baseline_requires_api_key(self):
        """Baseline should raise without API key."""
        import os
        from closureguard.baseline import baseline_detect

        # Temporarily clear env
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="API key required"):
                baseline_detect([{"text": "test", "action": "test"}])
        finally:
            if old_key:
                os.environ["ANTHROPIC_API_KEY"] = old_key
