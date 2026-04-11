"""Nous (νοῦς): Computational Reasoning Engine.

Makes reasoning into a computational object — inspectable, queryable,
forkable, and comparable. Like databases made text queryable, like git
made code branchable, Nous makes thought a first-class data structure.

The commitment graph is the foundation: a directed graph where nodes are
propositions and edges are entailment relations. Every query is a graph
traversal — deterministic, O(V+E), no LLM needed for structure.

Primary interface:
    from nous import Nous

    n = Nous()
    n.step("f is continuous on [a,b]", "Apply IVT")
    n.step("By IVT, root exists in (a,b)", "Find root")

    # SEE the structure
    n.state().assumptions()     # What's asserted without proof
    n.state().derived()         # What follows from assertions
    n.state().depends_on("root exists")  # Trace back

    # QUERY the structure
    n.state().gaps_to("f is differentiable")  # What's missing?
    n.state().circular()        # Any circular reasoning?
    n.state().weakest_link()    # Least supported commitment

    # MANIPULATE the structure
    with n.suppose("f is differentiable"):
        print(n.state().derived())  # Consequences
    # Auto-rolled back

    # COMPARE structures
    diff = n.diff(other_nous)

    # VISUALIZE
    n.show()                    # Interactive graph in browser
    print(n.state().summary())  # Terminal summary

    # VERIFY (existing capability)
    r = n.step("Since f is differentiable...", "Differentiate")
    r.coherent          # False — differentiability never proven
    r.violation          # Exact violation details

Backward compatible:
    from nous import ReasoningGuard  # still works
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__version__ = "0.5.0"
__all__ = [
    "Nous",
    "StepResult",
    "ReasoningGuard",
    "ClosureReport",
    "analyze_trace",
    "__version__",
]


def _load_dotenv() -> None:
    """Load .env file from project root if it exists."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not os.environ.get(key):
                os.environ[key] = value


_load_dotenv()


# ─── Primary interface ────────────────────────────────────────────────

# Violation types that have Lean soundness proofs → can reach "formal" certainty
_FORMAL_VIOLATION_TYPES: frozenset[str] = frozenset({
    "ModusPonensViolation",
    "ModalScopeError",
})

# Philosopher responsible for each violation class
_PHILOSOPHICAL_FRAMES: dict[str, str] = {
    "ModusPonensViolation": (
        "Aristotle — Syllogistic logic (Prior Analytics, 350 BC): "
        "if P is asserted and P→Q is asserted, Q must hold. "
        "This action treats Q as false while both P and P→Q are in the closure. "
        "Lean theorem: modusPonensSound in theory/ClosureViolation.lean."
    ),
    "ModalScopeError": (
        "Kripke — Possible-world semantics (Naming and Necessity, 1963): "
        "necessity (☐P) means P holds in ALL accessible worlds; "
        "possibility (◇P) means P holds in SOME. "
        "This step treats a necessity claim as merely possible, or vice versa. "
        "Lean theorem: modalScopeSound in theory/ClosureViolation.lean."
    ),
    "BeliefRevisionFailure": (
        "Brandom — Inferential commitment (Making It Explicit, 1994): "
        "new evidence that contradicts a prior belief demands explicit retraction. "
        "The agent received contradicting evidence but the original commitment persists "
        "unreised in the closure."
    ),
    "TemporalCoherenceViolation": (
        "Hintikka — Epistemic logic (Knowledge and Belief, 1962): "
        "K(P) at time T₁ entails a commitment to P at T₂ unless explicitly retracted. "
        "This step applies a belief from an earlier context without revalidating it."
    ),
    "ReferentialOpacityFailure": (
        "Peirce — Abductive inference (Collected Papers, 1903): "
        "co-referential substitution fails inside a belief context. "
        "'Lois knows Clark Kent flies' ≠ 'Lois knows Superman flies' "
        "even when Clark Kent = Superman. The substitution creates a new belief-action gap."
    ),
}

_CLEAN_FRAME = (
    "Hintikka — Epistemic closure maintained (Knowledge and Belief, 1962): "
    "K(P) ∧ K(P→Q) → K(Q). This step's action is consistent with all "
    "propositions in the commitment closure. No inferential commitment is violated."
)


def _compute_certainty(violation_dict: Optional[dict]) -> str:
    """Assign a certainty tier to a step verification result.

    Tiers:
        formal  — Lean-decidable violation type with high confidence (≥0.95).
                  The violation class has a soundness proof in theory/.
        high    — Multi-model consensus (reserved for Phase D.3 multi-model verifier).
        medium  — Single-model LLM detection (confidence ≥0.85), or clean step.
        low     — Below the review threshold; flagged but uncertain.
    """
    if not violation_dict:
        return "medium"  # clean step verified at single-model confidence
    vtype = violation_dict.get("type", "")
    confidence = float(violation_dict.get("confidence", 0.0))
    if vtype in _FORMAL_VIOLATION_TYPES and confidence >= 0.95:
        return "formal"
    if confidence >= 0.85:
        return "medium"
    return "low"


def _compute_justification(
    violation_dict: Optional[dict],
    certainty: str,
    closure_size: int,
) -> str:
    """Generate a human-readable justification for the certainty rating."""
    if not violation_dict:
        return (
            f"Step verified coherent: the action does not contradict any of "
            f"{closure_size} proposition(s) in the commitment closure."
        )
    vtype = violation_dict.get("type", "unknown")
    confidence = float(violation_dict.get("confidence", 0.0))
    explanation = violation_dict.get("explanation", "Action contradicts the commitment closure.")
    if certainty == "formal":
        return (
            f"Lean-decidable violation ({vtype}): this class of violation has a "
            f"soundness proof in theory/ClosureViolation.lean. Given explicitly stated "
            f"propositions, the violation is formally certain (confidence {confidence:.0%})."
        )
    if certainty == "medium":
        return f"Single-model LLM verification (confidence {confidence:.0%}): {explanation}"
    # low
    return (
        f"Confidence {confidence:.0%} is below the 0.85 threshold. "
        f"Violation is flagged for human review — treat as a strong signal, not a certainty."
    )


@dataclass
class StepResult:
    """Result of adding a step to the reasoning engine.

    Fields added in v0.5 (Phase D.2):
        certainty           — "formal" | "high" | "medium" | "low"
        justification       — why this certainty was assigned
        philosophical_frame — which philosopher's framework applies
        assumptions_surfaced — explicit beliefs extracted at this step
        new_commitments     — derived consequences now in the closure
    """
    step_index: int
    coherent: bool
    violation: Optional[dict] = None
    commitments_added: int = 0          # count, kept for backward compat
    total_commitments: int = 0
    closure_size: int = 0
    # Phase D.2 — metaphysical transparency layer
    certainty: str = "medium"
    justification: str = ""
    philosophical_frame: str = ""
    assumptions_surfaced: list = field(default_factory=list)
    new_commitments: list = field(default_factory=list)

    def __str__(self) -> str:
        if self.coherent:
            frame_short = self.philosophical_frame.split("—")[0].strip() if self.philosophical_frame else ""
            return (
                f"Step {self.step_index}: coherent [{self.certainty}] "
                f"(+{self.commitments_added} commitments, {self.closure_size} in closure)"
                + (f"\n  Frame: {frame_short}" if frame_short else "")
            )
        v = self.violation or {}
        return (
            f"Step {self.step_index}: VIOLATION [{self.certainty}] — {v.get('type', 'unknown')}\n"
            f"  Violated: {v.get('violated', '?')}\n"
            f"  Confidence: {v.get('confidence', 0):.0%}\n"
            f"  Justification: {self.justification}\n"
            f"  Frame: {self.philosophical_frame.split(chr(10))[0]}\n"
            f"  Chain:\n{v.get('chain', '')}"
        )

    def __bool__(self) -> bool:
        """StepResult is truthy when coherent."""
        return self.coherent


class Nous:
    """Computational Reasoning Engine.

    3 methods at core: step(), state(), closure().
    Everything else is a query on the graph.

    The engine maintains a commitment graph — a directed graph where
    nodes are propositions and edges are entailment relations. This
    graph IS the reasoning state, made formal and inspectable.

    Violations are detected by GRAPH TRAVERSAL, not by asking an LLM.
    The LLM is used only to extract structured propositions from
    natural language. Everything else is algorithmic.

    Args:
        backend: Entailment backend — "auto", "nli", "embedding", or "llm".
        provider: LLM provider for extraction — "anthropic", "openai", or "auto".
        api_key: API key for provider and/or entailment backend.
        entailment_threshold: Min confidence for entailment edges (0-1).
        contradiction_threshold: Min confidence for contradictions (0-1).

    Example:
        >>> n = Nous()
        >>> n.step("The catalyst is air-sensitive.", "Note requirements.")
        >>> n.step("Transfer under nitrogen.", "Transfer catalyst.")
        >>> r = n.step("Open flask to air.", "Add reagent.")
        >>> r.coherent  # False
        >>> r.violation['chain']  # Exact path showing the gap
    """

    def __init__(
        self,
        *,
        backend: str = "auto",
        provider: str = "auto",
        api_key: Optional[str] = None,
        entailment_threshold: float = 0.7,
        contradiction_threshold: float = 0.6,
    ):
        from nous.graph import CommitmentGraph
        from nous.entailment import get_backend as _get_backend
        from nous.trace import ReasoningTrace

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._provider_name = provider
        self._trace = ReasoningTrace()

        # Initialize entailment backend
        try:
            be = _get_backend(backend, api_key=self._api_key)
        except (RuntimeError, ImportError):
            be = None

        self._graph = CommitmentGraph(
            backend=be,
            api_key=self._api_key,
            entailment_threshold=entailment_threshold,
            contradiction_threshold=contradiction_threshold,
        )

    def step(
        self,
        reasoning: str,
        action: str = "",
        *,
        step_index: Optional[int] = None,
        test_mode: Optional[bool] = None,
    ) -> StepResult:
        """Add a reasoning step and check for violations.

        This is the primary method. Feed it reasoning (any source —
        human, AI, mixed) and it builds the commitment graph,
        computes closure, and checks for violations.

        Args:
            reasoning: What was said/thought at this step.
            action: What was done at this step.
            step_index: Optional step number (auto-increments if omitted).
            test_mode: Use built-in fixtures (no API). Auto-detects if None.

        Returns:
            StepResult with coherence status and any violation details.
        """
        from nous.trace import TraceEvent

        if test_mode is None:
            test_mode = not bool(self._api_key)

        pre_nodes = len(self._graph.nodes)
        idx = step_index or (self._graph._step_count + 1)

        # Record trace
        self._trace.set_step(idx)
        self._trace.record(
            TraceEvent.STEP_START,
            f"Processing: {reasoning[:80]}{'...' if len(reasoning) > 80 else ''}",
            action=action,
        )

        violation_path = self._graph.add_step(
            reasoning, action,
            step_index=step_index,
            test_mode=test_mode,
        )

        new_nodes = len(self._graph.nodes) - pre_nodes

        # Record node additions
        if new_nodes > 0:
            self._trace.record(
                TraceEvent.NODE_ADDED,
                f"{new_nodes} commitment(s) extracted",
                count=new_nodes,
            )

        closure = self._graph.get_closure()

        self._trace.record(
            TraceEvent.CLOSURE_COMPUTED,
            f"Closure: {len(closure)} commitments",
            size=len(closure),
        )

        violation_dict = None
        if violation_path:
            violation_dict = {
                "type": violation_path.violation_type,
                "confidence": violation_path.confidence,
                "action": violation_path.action,
                "violated": violation_path.violated_node.content,
                "step": violation_path.action_step,
                "chain": violation_path.format_chain(),
                "explanation": violation_path.explanation,
            }
            self._trace.record(
                TraceEvent.VIOLATION_FOUND,
                f"VIOLATION: {violation_path.violation_type} — {violation_path.violated_node.content[:60]}",
                violation_type=violation_path.violation_type,
                confidence=violation_path.confidence,
            )
        else:
            self._trace.record(
                TraceEvent.STEP_COMPLETE,
                "Step coherent",
            )

        # ── Phase D.2: certainty tier + philosophical transparency ──
        certainty = _compute_certainty(violation_dict)
        justification = _compute_justification(violation_dict, certainty, len(closure))
        philosophical_frame = (
            _PHILOSOPHICAL_FRAMES.get(violation_dict["type"], _CLEAN_FRAME)
            if violation_dict else _CLEAN_FRAME
        )

        # Nodes added at this step: explicit assertions and derived consequences
        step_nodes = [n for n in self._graph.nodes.values() if n.source_step == idx]
        assumptions_surfaced = [n.content for n in step_nodes if n.is_explicit]
        new_commitments_list = [n.content for n in step_nodes if not n.is_explicit]

        return StepResult(
            step_index=step_index or self._graph._step_count,
            coherent=violation_path is None,
            violation=violation_dict,
            commitments_added=new_nodes,
            total_commitments=len(self._graph.nodes),
            closure_size=len(closure),
            certainty=certainty,
            justification=justification,
            philosophical_frame=philosophical_frame,
            assumptions_surfaced=assumptions_surfaced,
            new_commitments=new_commitments_list,
        )

    def state(self) -> "ReasoningState":
        """Get the queryable reasoning state.

        Returns a ReasoningState object with methods to inspect,
        query, and analyze the commitment graph structure.
        """
        from nous.query import ReasoningState
        return ReasoningState(self._graph)

    def closure(self) -> list[str]:
        """Get all commitments the agent is currently bound to.

        This is the commitment closure — everything reachable from
        explicit assertions via entailment edges.
        Computed by BFS, O(V+E). No LLM.
        """
        return sorted(self._graph.get_closure())

    def suppose(self, *premises: str) -> "HypotheticalContext":
        """Explore a hypothetical: add premises, compute consequences, roll back.

        Kripke possible worlds — snapshot the current state, add
        temporary premises, let the user explore, then restore.

        Usage:
            with n.suppose("P = NP"):
                n.step("Then SAT is in P", "Derive")
                print(n.state().derived())
            # Original state preserved
        """
        from nous.query import HypotheticalContext
        from nous.trace import TraceEvent

        self._trace.record(
            TraceEvent.HYPOTHETICAL_ENTER,
            f"Suppose: {', '.join(premises[:3])}{'...' if len(premises) > 3 else ''}",
            premises=list(premises),
        )
        return HypotheticalContext(self._graph, *premises, trace=self._trace)

    def diff(self, other: "Nous") -> "ReasoningDiff":
        """Compare two reasoning paths structurally.

        Gentner's structure mapping: find what's shared,
        what diverges, and where the structural differences lie.
        """
        from nous.query import diff as _diff
        return _diff(self._graph, other._graph)

    def show(self, path: Optional[str] = None) -> str:
        """Open an interactive graph visualization in the browser.

        Uses Pyvis (vis.js) for force-directed, interactive graphs.
        Nodes are clickable, zoomable, draggable. Violations glow red.

        Args:
            path: Optional file path for the HTML. Uses tempfile if None.

        Returns:
            Path to the generated HTML file.

        Requires: pip install nous-ai[viz]
        """
        from nous.viz import show_graph, open_in_browser
        html_path = show_graph(self._graph, path=path)
        open_in_browser(html_path)
        return html_path

    def export_dot(self, path: Optional[str] = None) -> str:
        """Export the commitment graph as Graphviz DOT format."""
        dot = self._graph.to_dot()
        if path:
            with open(path, "w") as f:
                f.write(dot)
        return dot

    def trace(self) -> "ReasoningTrace":
        """Get the full reasoning trace for auditability.

        Every decision the engine makes is recorded — you can
        audit exactly why a violation was flagged or missed.
        """
        return self._trace

    @property
    def violations(self) -> list[dict]:
        """All violations detected so far."""
        return [
            {
                "type": v.violation_type,
                "confidence": v.confidence,
                "step": v.action_step,
                "violated": v.violated_node.content,
                "chain": v.format_chain(),
            }
            for v in self._graph.violations
        ]

    @property
    def graph(self):
        """Direct access to the underlying CommitmentGraph."""
        return self._graph

    def reset(self) -> None:
        """Clear all state. Use between reasoning sessions."""
        self._graph.reset()
        self._trace.clear()

    def _repr_html_(self) -> str:
        """Jupyter notebook inline rendering."""
        from nous.viz import graph_to_html
        return graph_to_html(self._graph)

    def __repr__(self) -> str:
        return (
            f"Nous(commitments={len(self._graph.nodes)}, "
            f"edges={len(self._graph.edges)}, "
            f"closure={len(self._graph.get_closure())}, "
            f"violations={len(self._graph.violations)})"
        )

    def __str__(self) -> str:
        """Pretty terminal output via Rich (falls back to plain text)."""
        from nous.viz import rich_print_state
        return rich_print_state(self._graph)


# ─── Backward compatibility ──────────────────────────────────────────
# from nous import ReasoningGuard still works
ReasoningGuard = Nous


# ─── Convenience wrapper (backward compatible) ────────────────────────

@dataclass
class ClosureReport:
    """High-level analysis report."""
    closure_score: float
    violation_count: int
    violations: list[dict] = field(default_factory=list)
    violation_breakdown: dict[str, int] = field(default_factory=dict)
    steps_analyzed: int = 0
    review_count: int = 0


def analyze_trace(
    trace: list[dict],
    *,
    batch: bool = True,
    test_mode: Optional[bool] = None,
    api_key: Optional[str] = None,
) -> ClosureReport:
    """Analyze a complete trace for violations.

    Routes through Nous.step() — single pipeline, no legacy code.

    Args:
        trace: List of dicts with 'text' and 'action' keys.
        test_mode: If True, use built-in fixtures. If None, auto-detect.
        api_key: Anthropic API key.

    Returns:
        ClosureReport with violations and scores.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if test_mode is None:
        test_mode = not bool(key)

    n = Nous(api_key=key)
    violation_dicts = []
    breakdown: dict[str, int] = {}

    for step in trace:
        text = step.get("text", "")
        action = step.get("action", "")
        step_index = step.get("step")

        r = n.step(
            text, action,
            step_index=step_index,
            test_mode=test_mode,
        )

        if not r.coherent and r.violation:
            v = r.violation
            vtype = v.get("type", "unknown")
            violation_dicts.append({
                "step_index": r.step_index,
                "antecedent": v.get("violated", ""),
                "entailed": v.get("explanation", ""),
                "action": v.get("action", ""),
                "violation_type": vtype,
                "confidence": v.get("confidence", 0.0),
                "needs_review": v.get("confidence", 0.0) < 0.85,
            })
            breakdown[vtype] = breakdown.get(vtype, 0) + 1

    num_violations = len(violation_dicts)
    score = min(1.0, num_violations / len(trace)) if trace else 0.0
    review_count = sum(1 for v in violation_dicts if v.get("needs_review"))

    return ClosureReport(
        closure_score=score,
        violation_count=num_violations,
        violations=violation_dicts,
        violation_breakdown=breakdown,
        steps_analyzed=len(trace),
        review_count=review_count,
    )
