"""Tests for new Nous features: trace, viz, strength, summary, StepResult."""

import pytest
from nous import Nous, StepResult


# ─── Trace Tests ─────────────────────────────────────────────────────

class TestTrace:
    """Test the reasoning trace for auditability."""

    def test_trace_records_steps(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        t = n.trace()
        assert len(t) >= 1

    def test_trace_records_violations(self):
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
        n.step(
            "Add the substrate and solvent. To ensure complete mixing, briefly open the flask to air to add the reagent via syringe.",
            "Open flask to air to add reagent.",
            test_mode=True,
        )
        violations = n.trace().violations_only()
        assert len(violations) >= 1

    def test_trace_summary(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        summary = n.trace().summary()
        assert "steps" in summary or "nodes" in summary

    def test_trace_for_step(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        entries = n.trace().for_step(1)
        assert len(entries) >= 1

    def test_trace_clears_on_reset(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        n.reset()
        assert len(n.trace()) == 0

    def test_trace_str(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        s = str(n.trace())
        assert len(s) > 0

    def test_trace_iter(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        entries = list(n.trace())
        assert len(entries) >= 1


# ─── StepResult Tests ────────────────────────────────────────────────

class TestStepResult:
    """Test StepResult pretty-printing and bool behavior."""

    def test_coherent_str(self):
        r = StepResult(step_index=1, coherent=True, commitments_added=2,
                       total_commitments=2, closure_size=3)
        s = str(r)
        assert "coherent" in s
        assert "Step 1" in s

    def test_incoherent_str(self):
        r = StepResult(step_index=3, coherent=False,
                       status="violation", certainty="formal",
                       violation={"type": "ModusPonensViolation",
                                  "violated": "catalyst is air-sensitive",
                                  "confidence": 0.95, "chain": "A -> B",
                                  "action": "open flask", "explanation": "contradiction"})
        s = str(r)
        assert "VIOLATION" in s
        assert "ModusPonensViolation" in s

    def test_bool_coherent(self):
        r = StepResult(step_index=1, coherent=True)
        assert r
        assert bool(r) is True

    def test_bool_incoherent(self):
        r = StepResult(step_index=1, coherent=False,
                       violation={"type": "X"})
        assert not r
        assert bool(r) is False


# ─── Strength & Summary Tests ────────────────────────────────────────

class TestStrengthAndSummary:
    """Test reasoning strength score and summary."""

    def test_strength_empty(self):
        n = Nous()
        s = n.state().strength()
        assert s == 1.0

    def test_strength_with_steps(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        s = n.state().strength()
        assert 0.0 <= s <= 1.0

    def test_strength_decreases_with_violations(self):
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
        strength_before = n.state().strength()

        n.step(
            "Add the substrate and solvent. To ensure complete mixing, briefly open the flask to air to add the reagent via syringe.",
            "Open flask to air to add reagent.",
            test_mode=True,
        )
        strength_after = n.state().strength()
        assert strength_after <= strength_before

    def test_summary_coherent(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        s = n.state().summary()
        assert "coherent" in s.lower()
        assert "assumptions" in s or "derived" in s or "strength" in s

    def test_summary_incoherent(self):
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
        n.step(
            "Add the substrate and solvent. To ensure complete mixing, briefly open the flask to air to add the reagent via syringe.",
            "Open flask to air to add reagent.",
            test_mode=True,
        )
        s = n.state().summary()
        assert "INCOHERENT" in s or "violation" in s.lower()


# ─── Visualization Tests ─────────────────────────────────────────────

class TestVisualization:
    """Test visualization integration."""

    def test_repr_html(self):
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
        html = n._repr_html_()
        assert "<div" in html
        assert "Nous" in html

    def test_repr_html_empty(self):
        n = Nous()
        html = n._repr_html_()
        assert "Empty" in html or "div" in html

    def test_str_output(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        s = str(n)
        assert "Nous" in s or "commitment" in s.lower() or "node" in s.lower()

    def test_show_generates_html(self):
        """show() should generate an HTML file (but we skip opening browser)."""
        import tempfile
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        # Use show_graph directly to avoid opening browser
        from nous.viz import show_graph
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            result = show_graph(n.graph, path=path)
            assert result == path
            with open(path) as f:
                content = f.read()
            assert "<html" in content.lower() or "vis" in content.lower()
        except ImportError:
            pytest.skip("pyvis not installed")
        finally:
            import os
            os.unlink(path)


# ─── GapAnalysis Method Attribute ────────────────────────────────────

class TestGapAnalysisMethod:
    """Test that gap analysis reports which method was used."""

    def test_reachable_is_exact(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        assumptions = n.state().assumptions()
        if assumptions:
            gap = n.state().gaps_to(assumptions[0])
            assert gap.method == "exact"

    def test_unreachable_is_heuristic(self):
        n = Nous()
        n.step("The number 42 is even.", "Store.", test_mode=True)
        gap = n.state().gaps_to("The reaction yield exceeds 95%")
        assert gap.method == "heuristic"
