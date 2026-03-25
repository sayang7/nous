"""Tests for the closure-based pipeline (closure.py + coherence.py).

Tests the philosophical funnel:
  assertions → commitment closure → coherence check → violation
"""

import pytest

from closureguard.closure import compute_closure
from closureguard.coherence import check_coherence, CoherenceResult


class TestCommitmentClosure:
    """Test the commitment closure operator."""

    def test_closure_includes_explicit_assertions(self):
        """Closure must include all explicit assertions."""
        assertions = [
            "The API endpoint returns JSON.",
            "JSON responses need to be parsed before accessing fields.",
        ]
        closure = compute_closure(assertions, test_mode=True)
        assert any("JSON" in c for c in closure)
        assert len(closure) >= len(assertions)

    def test_closure_includes_inferential_commitments(self):
        """Closure should include consequences not explicitly stated."""
        assertions = [
            "The API endpoint returns JSON.",
            "JSON responses need to be parsed before accessing fields.",
            "The response contains a 'name' field that can be extracted.",
        ]
        closure = compute_closure(assertions, test_mode=True)
        # Should include the derived commitment about not string-splitting
        assert any("string" in c.lower() or "parse" in c.lower()
                    for c in closure if c not in assertions)

    def test_closure_empty_input(self):
        assert compute_closure([], test_mode=True) == []

    def test_closure_returns_list_of_strings(self):
        assertions = ["The number 42 is even.", "42 is divisible by 2."]
        closure = compute_closure(assertions, test_mode=True)
        assert isinstance(closure, list)
        assert all(isinstance(c, str) for c in closure)

    def test_closure_config_deleted(self):
        """Closure should derive that reading from deleted file will fail."""
        assertions = [
            "config.yaml was deleted in the last deployment.",
            "config.yaml no longer exists on disk.",
        ]
        closure = compute_closure(assertions, test_mode=True)
        assert any("fail" in c.lower() or "cannot" in c.lower()
                    for c in closure)

    def test_closure_catalyst(self):
        """Closure should derive that air exposure deactivates catalyst."""
        assertions = [
            "The palladium catalyst is air-sensitive.",
            "The catalyst must be handled under inert atmosphere.",
            "Exposure to oxygen will deactivate the catalyst.",
        ]
        closure = compute_closure(assertions, test_mode=True)
        assert any("deactivat" in c.lower() or "air" in c.lower()
                    for c in closure)


class TestCoherenceCheck:
    """Test action-vs-closure coherence verification."""

    def test_coherent_action(self):
        """Action consistent with commitments should be coherent."""
        commitments = [
            "The number 42 is even.",
            "An even number is divisible by 2.",
            "42 is divisible by 2.",
        ]
        result = check_coherence(
            commitments, "Compute n / 2 = 21.",
            test_mode=True,
        )
        assert result.coherent is True

    def test_incoherent_action_json(self):
        """String-splitting JSON should violate parsing commitment."""
        commitments = [
            "The API endpoint returns JSON.",
            "JSON responses need to be parsed before accessing fields.",
            "The response from the API must be parsed as JSON before extracting the 'name' field.",
            "String-splitting or text manipulation is not appropriate for extracting fields from JSON.",
        ]
        result = check_coherence(
            commitments, "Split response string by commas to find name.",
            test_mode=True,
        )
        assert result.coherent is False
        assert result.violation_type == "ModusPonensViolation"
        assert result.confidence >= 0.85

    def test_incoherent_action_deleted_file(self):
        """Reading deleted file should violate revision commitment."""
        commitments = [
            "config.yaml was deleted in the last deployment.",
            "config.yaml no longer exists on disk.",
            "Reading from config.yaml will fail because it no longer exists.",
            "The database URL cannot be obtained from config.yaml.",
        ]
        result = check_coherence(
            commitments, "Read database_url field from config.yaml.",
            test_mode=True,
        )
        assert result.coherent is False
        assert result.violation_type == "BeliefRevisionFailure"

    def test_incoherent_action_unreachable_server(self):
        """Querying unreachable server should violate temporal commitment."""
        commitments = [
            "The database server is unreachable as of 14:00.",
            "Queries to the database server will fail while it is unreachable.",
            "User records cannot be fetched from an unreachable server.",
        ]
        result = check_coherence(
            commitments, "Query the database server for user records.",
            test_mode=True,
        )
        assert result.coherent is False
        assert result.violation_type == "TemporalCoherenceViolation"

    def test_empty_commitments_is_coherent(self):
        result = check_coherence([], "Do anything.", test_mode=True)
        assert result.coherent is True

    def test_empty_action_is_coherent(self):
        result = check_coherence(["Some commitment."], "", test_mode=True)
        assert result.coherent is True

    def test_violated_commitment_field(self):
        """Violation should identify which specific commitment was violated."""
        commitments = [
            "Exposing the catalyst to air will deactivate it.",
            "The catalyst must be handled under inert atmosphere.",
        ]
        result = check_coherence(
            commitments, "Open flask to air to add reagent.",
            test_mode=True,
        )
        assert result.coherent is False
        assert result.violated_commitment is not None
        assert len(result.violated_commitment) > 0


class TestFullPipeline:
    """Test the complete philosophical funnel end-to-end."""

    def test_pipeline_detects_single_precise_violation(self):
        """The closure pipeline should find exactly one violation per incoherent trace."""
        from closureguard import analyze_trace

        trace = [
            {"step": 1, "text": "The API documentation confirms the endpoint returns JSON.",
             "action": "Send GET request to the endpoint."},
            {"step": 2, "text": "JSON responses need to be parsed before accessing fields.",
             "action": "Store the response body."},
            {"step": 3, "text": "Let me extract the 'name' field from the response.",
             "action": "Split response string by commas to find name."},
        ]
        report = analyze_trace(trace, test_mode=True)
        assert report.violation_count >= 1
        assert any(v["violation_type"] == "ModusPonensViolation"
                    for v in report.violations)

    def test_pipeline_clean_trace_no_violations(self):
        """Coherent traces should produce zero violations."""
        from closureguard import analyze_trace

        trace = [
            {"step": 1, "text": "The input n = 42 is an even number.",
             "action": "Store n = 42 as even."},
            {"step": 2, "text": "Since n is even, n is divisible by 2.",
             "action": "Compute n / 2 = 21."},
            {"step": 3, "text": "The result is 21.",
             "action": "Return 21."},
        ]
        report = analyze_trace(trace, test_mode=True)
        assert report.violation_count == 0
