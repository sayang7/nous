"""Tests for the Nous computational reasoning engine.

Tests the new query interface: assumptions, derived, depends_on,
circular, gaps_to, suppose, diff, and the Nous class itself.
"""

import pytest

from nous import Nous, ReasoningGuard, StepResult


# ─── Nous Class Tests ────────────────────────────────────────────────

class TestNous:
    """Test the primary Nous interface."""

    def test_step_coherent(self):
        """Coherent steps should return coherent=True."""
        n = Nous()
        r1 = n.step(
            "The input n = 42 is an even number.",
            "Store n = 42 as even.",
            test_mode=True,
        )
        assert r1.coherent
        assert r1.total_commitments >= 1

    def test_step_detects_violation(self):
        """Violations should be detected via graph traversal."""
        n = Nous()
        n.step(
            "The palladium catalyst is air-sensitive and must be handled under inert atmosphere (N2 or Ar). Exposure to oxygen will deactivate it.",
            "Note catalyst requirements.",
            test_mode=True,
        )
        n.step(
            "Weigh 50mg of catalyst in the glovebox and transfer to the Schlenk flask under nitrogen.",
            "Transfer catalyst under nitrogen.",
            test_mode=True,
        )
        r = n.step(
            "Add the substrate and solvent. To ensure complete mixing, briefly open the flask to air to add the reagent via syringe.",
            "Open flask to air to add reagent.",
            test_mode=True,
        )
        assert not r.coherent
        assert r.violation is not None
        assert "type" in r.violation

    def test_closure_returns_sorted_list(self):
        n = Nous()
        n.step("The number 42 is even.", "Store it.", test_mode=True)
        c = n.closure()
        assert isinstance(c, list)
        assert c == sorted(c)

    def test_violations_property(self):
        n = Nous()
        assert n.violations == []

    def test_reset(self):
        n = Nous()
        n.step("Something.", "Do.", test_mode=True)
        n.reset()
        assert n.closure() == []
        assert n.violations == []

    def test_repr(self):
        n = Nous()
        assert "Nous(" in repr(n)

    def test_backward_compat_reasoning_guard(self):
        """ReasoningGuard should be an alias for Nous."""
        assert ReasoningGuard is Nous
        guard = ReasoningGuard()
        assert isinstance(guard, Nous)


# ─── ReasoningState Tests ────────────────────────────────────────────

class TestReasoningState:
    """Test structural queries on the commitment graph."""

    def _build_nous(self):
        """Build a Nous with a chemistry protocol trace."""
        n = Nous()
        n.step(
            "The palladium catalyst is air-sensitive and must be handled under inert atmosphere (N2 or Ar). Exposure to oxygen will deactivate it.",
            "Note catalyst requirements.",
            test_mode=True,
        )
        n.step(
            "Weigh 50mg of catalyst in the glovebox and transfer to the Schlenk flask under nitrogen.",
            "Transfer catalyst under nitrogen.",
            test_mode=True,
        )
        return n

    def test_assumptions(self):
        """assumptions() should return explicit assertions."""
        n = self._build_nous()
        s = n.state()
        assumptions = s.assumptions()
        assert len(assumptions) >= 1
        assert all(isinstance(a, str) for a in assumptions)

    def test_derived(self):
        """derived() should return non-explicit commitments."""
        n = self._build_nous()
        s = n.state()
        derived = s.derived()
        assert isinstance(derived, list)
        # Derived commitments should not overlap with assumptions
        assumptions_set = set(s.assumptions())
        for d in derived:
            assert d not in assumptions_set

    def test_depends_on_existing(self):
        """depends_on() should trace back to foundations."""
        n = self._build_nous()
        s = n.state()
        assumptions = s.assumptions()
        if assumptions:
            deps = s.depends_on(assumptions[0])
            assert isinstance(deps, list)

    def test_depends_on_missing(self):
        """depends_on() for nonexistent node returns empty."""
        n = Nous()
        s = n.state()
        assert s.depends_on("nonexistent proposition") == []

    def test_circular_no_cycles(self):
        """A normal trace should have no circular reasoning."""
        n = self._build_nous()
        s = n.state()
        cycles = s.circular()
        assert isinstance(cycles, list)
        # Normal reasoning shouldn't be circular
        assert len(cycles) == 0

    def test_gaps_to_reachable(self):
        """gaps_to() for a reachable goal should say reachable=True."""
        n = self._build_nous()
        s = n.state()
        assumptions = s.assumptions()
        if assumptions:
            gap = s.gaps_to(assumptions[0])
            assert gap.reachable

    def test_gaps_to_unreachable(self):
        """gaps_to() for an unreachable goal should suggest premises."""
        n = self._build_nous()
        s = n.state()
        gap = s.gaps_to("The reaction yield exceeds 95%")
        assert not gap.reachable
        assert isinstance(gap.suggested_premises, list)

    def test_weakest_link(self):
        """weakest_link() should return a string or None."""
        n = self._build_nous()
        s = n.state()
        wl = s.weakest_link()
        assert wl is None or isinstance(wl, str)

    def test_dot_export(self):
        """dot() should return valid DOT format."""
        n = self._build_nous()
        s = n.state()
        dot = s.dot()
        assert "digraph" in dot

    def test_to_dict(self):
        """to_dict() should return serializable dict."""
        n = self._build_nous()
        s = n.state()
        d = s.to_dict()
        assert "nodes" in d
        assert "edges" in d

    def test_repr(self):
        n = self._build_nous()
        s = n.state()
        assert "ReasoningState(" in repr(s)


# ─── HypotheticalContext Tests ───────────────────────────────────────

class TestSuppose:
    """Test hypothetical exploration (Kripke possible worlds)."""

    def test_suppose_adds_and_rolls_back(self):
        """suppose() should add premises then restore original state."""
        n = Nous()
        n.step("The number 42 is even.", "Store it.", test_mode=True)
        original_closure = n.closure()

        with n.suppose("All even numbers are prime"):
            # Inside: the premise should be in the graph
            hyp_closure = n.closure()
            assert "All even numbers are prime" in hyp_closure

        # Outside: original state restored
        assert n.closure() == original_closure

    def test_suppose_state_queryable(self):
        """Inside suppose, state() should reflect hypothetical."""
        n = Nous()
        n.step("The number 42 is even.", "Store it.", test_mode=True)

        with n.suppose("42 is also odd") as hyp:
            s = hyp.state()
            assumptions = s.assumptions()
            assert "42 is also odd" in assumptions

    def test_suppose_multiple_premises(self):
        """suppose() should accept multiple premises."""
        n = Nous()
        with n.suppose("P = NP", "Factoring is in P") as hyp:
            assumptions = hyp.state().assumptions()
            assert "P = NP" in assumptions
            assert "Factoring is in P" in assumptions


# ─── Diff Tests ──────────────────────────────────────────────────────

class TestDiff:
    """Test reasoning comparison (Gentner structure mapping)."""

    def test_diff_identical(self):
        """Diffing identical reasoning should show all shared."""
        n1 = Nous()
        n2 = Nous()
        # Use a multi-step trace so the graph has nodes in its closure
        n1.step("The input n = 42 is an even number.", "Store.", test_mode=True)
        n1.step("Since n is even, n is divisible by 2.", "Divide.", test_mode=True)
        n2.step("The input n = 42 is an even number.", "Store.", test_mode=True)
        n2.step("Since n is even, n is divisible by 2.", "Divide.", test_mode=True)

        d = n1.diff(n2)
        assert len(d.only_in_left) == 0
        assert len(d.only_in_right) == 0
        assert len(d.shared) >= 1

    def test_diff_divergent(self):
        """Diffing divergent reasoning should show differences."""
        n1 = Nous()
        n2 = Nous()
        n1.step("The number 42 is even.", "Store.", test_mode=True)
        n2.step(
            "The API documentation confirms the endpoint returns JSON.",
            "Send request.",
            test_mode=True,
        )

        d = n1.diff(n2)
        assert len(d.only_in_left) >= 1 or len(d.only_in_right) >= 1

    def test_diff_has_structural_differences(self):
        """Diff should report structural (edge) differences."""
        n1 = Nous()
        n2 = Nous()
        n1.step("The number 42 is even.", "Store.", test_mode=True)

        d = n1.diff(n2)
        assert isinstance(d.structural_differences, list)


# ─── Analyze Trace Tests ─────────────────────────────────────────────

class TestAnalyzeTrace:
    """Test backward-compatible analyze_trace."""

    def test_analyze_violation(self):
        from nous import analyze_trace

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

    def test_analyze_clean(self):
        from nous import analyze_trace

        trace = [
            {"step": 1, "text": "The input n = 42 is an even number.",
             "action": "Store n = 42 as even."},
            {"step": 2, "text": "Since n is even, n is divisible by 2.",
             "action": "Compute n / 2 = 21."},
        ]
        report = analyze_trace(trace, test_mode=True)
        assert report.violation_count == 0
