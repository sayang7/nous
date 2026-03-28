"""Structural queries on the commitment graph.

Pure graph algorithms. Zero LLM calls. This is what makes Nous
different from every other tool: reasoning as a queryable data structure.

Every method here is a graph traversal — O(V+E) or better.
The graph IS the reasoning. These queries make it inspectable.

Philosophical grounding:
  - assumptions() → Brandom: what's in the base (explicit commitments)
  - derived() → Brandom: inferential role (what follows from base)
  - depends_on() → Kripke: accessibility (what worlds reach this one)
  - gaps_to() → Peirce: abduction (what's missing to reach a goal)
  - circular() → soundness: cycle detection (reasoning can't be circular)
  - weakest_link() → confidence propagation (min-confidence path)
  - suppose() → Kripke: possible worlds (add premise, explore, roll back)
  - diff() → Gentner: structural mapping (compare two reasoning paths)
"""

from __future__ import annotations

import copy
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nous.graph import CommitmentGraph, CommitmentNode, EntailmentEdge


@dataclass
class GapAnalysis:
    """Result of analyzing what's missing to reach a goal."""
    goal: str
    reachable: bool
    closest_nodes: list[str]
    missing_links: list[str]
    suggested_premises: list[str]
    method: str = "heuristic"  # "heuristic" or "semantic"


@dataclass
class ReasoningDiff:
    """Structural difference between two reasoning paths."""
    only_in_left: list[str]
    only_in_right: list[str]
    shared: list[str]
    structural_differences: list[str]


class ReasoningState:
    """Queryable reasoning structure. All methods are graph traversals.

    This is the core abstraction: reasoning as a computational object
    you can inspect, query, and manipulate — not just read as text.
    """

    def __init__(self, graph: CommitmentGraph):
        self._graph = graph

    def assumptions(self) -> list[str]:
        """What the agent explicitly asserted (without derivation).

        These are the foundations — everything else is built on these.
        O(V) — single pass over nodes.
        """
        return sorted(
            content
            for content, node in self._graph.nodes.items()
            if node.is_explicit
        )

    def derived(self) -> list[str]:
        """What follows from the assumptions via entailment.

        These are the inferential commitments — things the agent
        is committed to even if it never said them explicitly.
        O(V+E) — BFS to compute closure, then subtract assumptions.
        """
        closure = self._graph.get_closure()
        explicit = {
            content
            for content, node in self._graph.nodes.items()
            if node.is_explicit
        }
        return sorted(closure - explicit)

    def depends_on(self, proposition: str) -> list[str]:
        """Trace back to foundations: what does this proposition depend on?

        Reverse BFS from the given node — follows edges BACKWARD
        to find all premises that support this conclusion.
        O(V+E).
        """
        if proposition not in self._graph.nodes:
            return []

        # Build reverse adjacency
        reverse_adj: dict[str, list[str]] = {}
        for edge in self._graph.edges:
            p, c = edge.premise.content, edge.consequence.content
            reverse_adj.setdefault(c, []).append(p)

        # BFS backward
        visited: set[str] = set()
        queue: deque[str] = deque([proposition])
        result: list[str] = []

        while queue:
            current = queue.popleft()
            for parent in reverse_adj.get(current, []):
                if parent not in visited:
                    visited.add(parent)
                    result.append(parent)
                    queue.append(parent)

        return sorted(result)

    def gaps_to(self, goal: str) -> GapAnalysis:
        """What's missing to reach a goal from current commitments?

        Abductive reasoning (Peirce): observe that we want Q,
        figure out what P would get us there.

        Uses lazy semantic upgrade: tries entailment backend if available,
        falls back to word-overlap heuristic. The .method attribute on the
        result tells you which was used.
        """
        closure = self._graph.get_closure()

        # Is the goal already reachable?
        if goal in closure:
            return GapAnalysis(
                goal=goal,
                reachable=True,
                closest_nodes=[goal],
                missing_links=[],
                suggested_premises=[],
                method="exact",
            )

        # Try semantic check via entailment backend
        method = "heuristic"
        semantic_closest: list[tuple[float, str]] = []

        if self._graph._backend_initialized and self._graph._backend is not None:
            try:
                backend = self._graph._backend
                for content in closure:
                    result = backend.check_entailment(content, goal)
                    if result.confidence > 0.3:
                        semantic_closest.append((result.confidence, content))
                if semantic_closest:
                    method = "semantic"
            except Exception:
                semantic_closest = []

        # Fall back to word-overlap heuristic
        if not semantic_closest:
            goal_words = set(goal.lower().split())
            for content in closure:
                content_words = set(content.lower().split())
                if not goal_words or not content_words:
                    continue
                overlap = len(goal_words & content_words) / len(goal_words | content_words)
                if overlap > 0:
                    semantic_closest.append((overlap, content))

        semantic_closest.sort(reverse=True)
        closest = [content for _, content in semantic_closest[:3]]

        # Suggest what premises would bridge the gap
        missing = []
        suggested = []
        if closest:
            for c in closest:
                missing.append(f"{c} -> {goal}")
                suggested.append(f"If {c.rstrip('.')}, then {goal.lower()}")
        else:
            missing.append(f"No path to: {goal}")
            suggested.append(goal)

        return GapAnalysis(
            goal=goal,
            reachable=False,
            closest_nodes=closest,
            missing_links=missing,
            suggested_premises=suggested,
            method=method,
        )

    def circular(self) -> list[list[str]]:
        """Detect circular reasoning via Tarjan's SCC algorithm.

        Returns list of cycles (each cycle is a list of propositions).
        The #1 failure mode in informal proofs. O(V+E).
        """
        index_counter = [0]
        stack: list[str] = []
        on_stack: set[str] = set()
        indices: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        cycles: list[list[str]] = []

        def strongconnect(v: str) -> None:
            indices[v] = index_counter[0]
            lowlinks[v] = index_counter[0]
            index_counter[0] += 1
            stack.append(v)
            on_stack.add(v)

            for w in self._graph.adjacency.get(v, []):
                if w not in indices:
                    strongconnect(w)
                    lowlinks[v] = min(lowlinks[v], lowlinks[w])
                elif w in on_stack:
                    lowlinks[v] = min(lowlinks[v], indices[w])

            if lowlinks[v] == indices[v]:
                component: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    component.append(w)
                    if w == v:
                        break
                # Only report cycles (SCCs with >1 node or self-loops)
                if len(component) > 1:
                    cycles.append(sorted(component))
                elif component[0] in self._graph.adjacency.get(component[0], []):
                    cycles.append(component)

        for node in self._graph.nodes:
            if node not in indices:
                strongconnect(node)

        return cycles

    def weakest_link(self) -> Optional[str]:
        """Find the proposition with the lowest confidence support.

        Propagates confidence along edges — the weakest link is the
        node whose best supporting path has the lowest minimum confidence.
        O(V+E).
        """
        if not self._graph.nodes:
            return None

        # Build confidence map: for each node, what's the max min-confidence
        # path from any explicit assertion to it?
        explicit = [
            content for content, node in self._graph.nodes.items()
            if node.is_explicit
        ]
        if not explicit:
            return None

        # Edge confidence lookup
        edge_conf: dict[tuple[str, str], float] = {}
        for edge in self._graph.edges:
            key = (edge.premise.content, edge.consequence.content)
            edge_conf[key] = max(edge_conf.get(key, 0.0), edge.confidence)

        # Modified Dijkstra: maximize the minimum confidence along any path
        best_conf: dict[str, float] = {e: 1.0 for e in explicit}
        queue: deque[str] = deque(explicit)

        while queue:
            current = queue.popleft()
            for neighbor in self._graph.adjacency.get(current, []):
                ec = edge_conf.get((current, neighbor), 1.0)
                path_conf = min(best_conf[current], ec)
                if path_conf > best_conf.get(neighbor, 0.0):
                    best_conf[neighbor] = path_conf
                    queue.append(neighbor)

        # Find the derived node with lowest confidence
        derived_confs = {
            content: conf
            for content, conf in best_conf.items()
            if content not in explicit and conf < 1.0
        }
        if not derived_confs:
            # All nodes are explicit or have full confidence
            # Return the node with lowest edge confidence
            all_confs = {content: conf for content, conf in best_conf.items()}
            if all_confs:
                return min(all_confs, key=all_confs.get)
            return None

        return min(derived_confs, key=derived_confs.get)

    def strength(self) -> float:
        """Overall reasoning strength score (0-1).

        Combines: proportion of supported nodes, absence of cycles,
        and minimum confidence across all edges.
        """
        if not self._graph.nodes:
            return 1.0

        closure = self._graph.get_closure()
        total = len(self._graph.nodes)
        if total == 0:
            return 1.0

        # Coverage: what fraction of nodes are in the closure?
        coverage = len(closure) / total

        # Confidence: minimum edge confidence (1.0 if no edges)
        min_conf = 1.0
        for edge in self._graph.edges:
            min_conf = min(min_conf, edge.confidence)

        # Cycles: penalty for circular reasoning
        cycles = self.circular()
        cycle_penalty = 1.0 if not cycles else max(0.0, 1.0 - 0.2 * len(cycles))

        # Violations: penalty
        violation_penalty = 1.0 if not self._graph.violations else max(
            0.0, 1.0 - 0.3 * len(self._graph.violations)
        )

        return round(coverage * min_conf * cycle_penalty * violation_penalty, 3)

    def summary(self) -> str:
        """Human-readable summary of the reasoning state."""
        n_assumptions = len(self.assumptions())
        n_derived = len(self.derived())
        n_edges = len(self._graph.edges)
        n_violations = len(self._graph.violations)
        n_cycles = len(self.circular())
        s = self.strength()

        parts = [f"{n_assumptions} assumptions, {n_derived} derived, {n_edges} edges"]
        if n_violations > 0:
            parts.append(f"{n_violations} violation(s)")
        if n_cycles > 0:
            parts.append(f"{n_cycles} cycle(s)")
        parts.append(f"strength={s:.0%}")

        status = "INCOHERENT" if n_violations > 0 else "coherent"
        return f"[{status}] {', '.join(parts)}"

    def dot(self) -> str:
        """Export as Graphviz DOT format for visualization."""
        return self._graph.to_dot()

    def to_dict(self) -> dict:
        """Full state as a serializable dict."""
        return self._graph.to_dict()

    def __repr__(self) -> str:
        return (
            f"ReasoningState(assumptions={len(self.assumptions())}, "
            f"derived={len(self.derived())}, "
            f"edges={len(self._graph.edges)})"
        )


class HypotheticalContext:
    """Context manager for 'suppose P' exploration.

    Kripke possible worlds: snapshot the graph DATA (not the backend),
    add temporary premises, compute consequences, then roll back on exit.
    The original reasoning state is preserved.

    Usage:
        with HypotheticalContext(graph, "P = NP") as hyp:
            hyp.step("Then SAT is in P", "Derive consequences")
            print(hyp.state().derived())
        # Original state restored
    """

    def __init__(self, graph: CommitmentGraph, *premises: str, trace=None):
        self._graph = graph
        self._premises = premises
        self._trace = trace  # Optional ReasoningTrace for recording events
        # Snapshot only graph data, NOT the backend (avoids deep-copying
        # PyTorch models, HTTP clients, etc.)
        self._snapshot_nodes: dict = {}
        self._snapshot_edges: list = []
        self._snapshot_adjacency: dict = {}
        self._snapshot_violations: list = []
        self._snapshot_step_count: int = 0

    def __enter__(self) -> HypotheticalContext:
        # Deep snapshot of graph DATA only (not backend)
        self._snapshot_nodes = copy.deepcopy(self._graph.nodes)
        self._snapshot_edges = copy.deepcopy(self._graph.edges)
        self._snapshot_adjacency = copy.deepcopy(self._graph.adjacency)
        self._snapshot_violations = copy.deepcopy(self._graph.violations)
        self._snapshot_step_count = self._graph._step_count

        # Add hypothetical premises as explicit nodes
        from nous.graph import CommitmentNode
        for premise in self._premises:
            if premise not in self._graph.nodes:
                node = CommitmentNode(
                    content=premise,
                    source_step=self._graph._step_count + 1,
                    is_explicit=True,
                    modality="asserted",
                )
                self._graph.nodes[premise] = node
                self._graph.adjacency[premise] = []

        # Compute entailment edges for the new premises against existing nodes
        # This makes suppose() actually useful — you can see what the premise entails
        self._compute_hypothetical_edges()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Record trace event before rollback
        if self._trace is not None:
            from nous.trace import TraceEvent
            self._trace.record(
                TraceEvent.HYPOTHETICAL_EXIT,
                f"Exiting suppose: {', '.join(self._premises[:3])}{'...' if len(self._premises) > 3 else ''}",
                premises=list(self._premises),
            )
        # Roll back to snapshot
        self._graph.nodes = self._snapshot_nodes
        self._graph.edges = self._snapshot_edges
        self._graph.adjacency = self._snapshot_adjacency
        self._graph.violations = self._snapshot_violations
        self._graph._step_count = self._snapshot_step_count

    def _compute_hypothetical_edges(self) -> None:
        """Compute entailment edges for hypothetical premises.

        Uses the backend if available, otherwise skips (premises are
        still in the graph as isolated nodes, which is fine for test mode).
        """
        if not self._graph._backend_initialized or self._graph._backend is None:
            return

        backend = self._graph._backend
        from nous.graph import EntailmentEdge

        new_nodes = [
            self._graph.nodes[p] for p in self._premises
            if p in self._graph.nodes
        ]
        existing_nodes = [
            n for c, n in self._graph.nodes.items()
            if c not in self._premises
        ]

        threshold = self._graph._entailment_threshold

        for new_node in new_nodes:
            for existing_node in existing_nodes:
                try:
                    # Does existing → new?
                    result = backend.check_entailment(
                        existing_node.content, new_node.content,
                    )
                    if result.relation == "entailment" and result.confidence >= threshold:
                        edge = EntailmentEdge(
                            premise=existing_node,
                            consequence=new_node,
                            rule="hypothetical",
                            confidence=result.confidence,
                        )
                        self._graph.edges.append(edge)
                        self._graph.adjacency.setdefault(
                            existing_node.content, []
                        ).append(new_node.content)

                    # Does new → existing?
                    result = backend.check_entailment(
                        new_node.content, existing_node.content,
                    )
                    if result.relation == "entailment" and result.confidence >= threshold:
                        edge = EntailmentEdge(
                            premise=new_node,
                            consequence=existing_node,
                            rule="hypothetical",
                            confidence=result.confidence,
                        )
                        self._graph.edges.append(edge)
                        self._graph.adjacency.setdefault(
                            new_node.content, []
                        ).append(existing_node.content)
                except Exception:
                    # If backend fails during hypothetical, just skip edges
                    continue

    def step(self, reasoning: str, action: str = "", **kwargs) -> None:
        """Add a step within the hypothetical context."""
        self._graph.add_step(reasoning, action, test_mode=True, **kwargs)

    def state(self) -> ReasoningState:
        """Query the hypothetical reasoning state."""
        return ReasoningState(self._graph)

    def closure(self) -> list[str]:
        """Get closure within the hypothetical context."""
        return sorted(self._graph.get_closure())

    def contradictions(self) -> list[dict]:
        """Get any contradictions found in the hypothetical."""
        return [
            {
                "type": v.violation_type,
                "confidence": v.confidence,
                "violated": v.violated_node.content,
                "chain": v.format_chain(),
            }
            for v in self._graph.violations
            if v not in self._snapshot_violations
        ]


def diff(left: CommitmentGraph, right: CommitmentGraph) -> ReasoningDiff:
    """Compare two reasoning paths structurally.

    Gentner's structure mapping: find what's shared, what diverges,
    and where the structural differences lie.
    """
    left_closure = left.get_closure()
    right_closure = right.get_closure()

    shared = left_closure & right_closure
    only_left = left_closure - right_closure
    only_right = right_closure - left_closure

    # Find structural differences: edges that exist in one but not the other
    left_edge_set = {
        (e.premise.content, e.consequence.content) for e in left.edges
    }
    right_edge_set = {
        (e.premise.content, e.consequence.content) for e in right.edges
    }

    structural_diffs = []
    for p, c in left_edge_set - right_edge_set:
        structural_diffs.append(f"Left only: {p} -> {c}")
    for p, c in right_edge_set - left_edge_set:
        structural_diffs.append(f"Right only: {p} -> {c}")

    return ReasoningDiff(
        only_in_left=sorted(only_left),
        only_in_right=sorted(only_right),
        shared=sorted(shared),
        structural_differences=sorted(structural_diffs),
    )
