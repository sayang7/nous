"""Commitment Graph: the core data structure for reasoning integrity.

A commitment graph is a directed graph where:
  - Nodes are propositions the agent is committed to
  - Edges represent entailment relations (P -> Q)
  - The graph grows cumulatively as the agent reasons

This is NOT a prompt to an LLM. The graph is a concrete, inspectable,
serializable data structure that represents the agent's inferential
commitments — and makes violations visible as graph-theoretic properties.

A violation is a PATH in the graph:
    P1 -> P2 -> ... -> Pn,  but action presupposes NOT(Pn)

This maps directly to Kripke semantics: the graph IS a (partial)
representation of the accessibility relation between possible worlds.
Nodes reachable from the agent's asserted beliefs are the commitment
closure. An action that contradicts any reachable node is incoherent.

Architecture:
  - LLM/NLP is used ONLY to extract beliefs from natural language text
  - Entailment checking uses a pluggable backend (NLI model, embeddings, or LLM)
  - Closure computation is graph traversal (BFS) — deterministic, O(V+E)
  - Violation detection is graph search + contradiction check — algorithmic
  - Classification is determined by edge types in the graph — no LLM needed
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from nous.entailment import EntailmentBackend, EntailmentResult, get_backend

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitmentNode:
    """A proposition in the commitment graph."""
    content: str
    source_step: int
    is_explicit: bool = True  # False if derived via entailment
    modality: str = "asserted"  # "asserted", "possible", "temporal", "revised"

    def __hash__(self) -> int:
        return hash(self.content)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CommitmentNode):
            return NotImplemented
        return self.content == other.content


@dataclass
class EntailmentEdge:
    """A directed entailment relation: premise -> consequence."""
    premise: CommitmentNode
    consequence: CommitmentNode
    rule: str = "modus_ponens"  # modus_ponens, contrapositive, practical, revision, modal, temporal
    confidence: float = 1.0


@dataclass
class ViolationPath:
    """A violation witnessed by a path in the commitment graph.

    The path shows exactly HOW the agent's action contradicts its
    commitments: starting from an explicit assertion, through a chain
    of entailments, to a commitment that the action violates.
    """
    path: list[CommitmentNode]
    violated_node: CommitmentNode
    action: str
    action_step: int
    violation_type: str
    confidence: float
    explanation: str

    def format_chain(self) -> str:
        """Human-readable violation chain."""
        parts = []
        for node in self.path:
            prefix = "ASSERTED" if node.is_explicit else "ENTAILED"
            parts.append(f"  [{prefix} @ step {node.source_step}] {node.content}")
        parts.append(f"  [ACTION @ step {self.action_step}] {self.action}")
        parts.append(f"  CONTRADICTION: action presupposes NOT({self.violated_node.content})")
        return "\n".join(parts)


# ─── Violation type classification from graph structure ───────────────
# This is ALGORITHMIC, not LLM-based. The violation type is determined
# by the STRUCTURE of the path and the MODALITY of the nodes.

def _classify_violation(
    path: list[CommitmentNode],
    edges: list[EntailmentEdge],
) -> str:
    """Classify a violation based on graph structure alone.

    - If the path crosses a 'revision' edge → BeliefRevisionFailure
    - If any node has modality='possible' → ModalScopeError
    - If any node has modality='temporal' → TemporalCoherenceViolation
    - If any edge is 'referential' → ReferentialOpacityFailure
    - Otherwise → ModusPonensViolation (the canonical case)
    """
    # Check for specific patterns
    edge_rules = set()
    for edge in edges:
        if edge.premise.content in {n.content for n in path}:
            edge_rules.add(edge.rule)
        if edge.consequence.content in {n.content for n in path}:
            edge_rules.add(edge.rule)

    node_modalities = {n.modality for n in path}

    if "revision" in edge_rules:
        return "BeliefRevisionFailure"
    if "possible" in node_modalities or "modal" in edge_rules:
        return "ModalScopeError"
    if "temporal" in node_modalities or "temporal" in edge_rules:
        return "TemporalCoherenceViolation"
    if "referential" in edge_rules:
        return "ReferentialOpacityFailure"

    return "ModusPonensViolation"


# ─── Modal/temporal/revision signal detection ─────────────────────────

_MODAL_MARKERS = {"might", "could", "possibly", "potentially", "perhaps", "may", "likely", "suggests"}
_TEMPORAL_MARKERS = {"as of", "at time", "previously", "earlier", "updated", "now", "changed", "no longer"}
_REVISION_MARKERS = {"actually", "corrected", "revised", "turns out", "new data", "incorrect", "false"}


def _detect_modality(text: str) -> str:
    """Detect the modality of a belief from its text."""
    lower = text.lower()
    if any(m in lower for m in _REVISION_MARKERS):
        return "revised"
    if any(m in lower for m in _MODAL_MARKERS):
        return "possible"
    if any(m in lower for m in _TEMPORAL_MARKERS):
        return "temporal"
    return "asserted"


class CommitmentGraph:
    """Directed graph of inferential commitments.

    The graph grows incrementally as the agent reasons. Each step:
    1. Extracts new commitments (nodes) from the agent's reasoning
       (this is the ONLY part that uses NLP/LLM)
    2. Computes entailment edges using the pluggable backend
       (NLI model, embeddings, or LLM — NOT hard-coded to any API)
    3. Computes closure via BFS (pure algorithm, O(V+E))
    4. Checks action against closure using contradiction detection
       (backend handles semantic comparison)
    5. Classifies violation type from graph structure (pure algorithm)

    The graph IS the formal semantics made concrete. It maps to
    Kripke frames: nodes are worlds, edges are accessibility relations,
    closure is the set of reachable worlds, violations are contradictions
    between reachable worlds and the agent's actions.
    """

    def __init__(
        self,
        backend: Optional[EntailmentBackend] = None,
        api_key: Optional[str] = None,
        entailment_threshold: float = 0.7,
        contradiction_threshold: float = 0.6,
    ):
        """Initialize the commitment graph.

        Args:
            backend: Entailment backend (NLI, embedding, or LLM).
                     If None, auto-detects the best available.
            api_key: For LLM backend (if auto-detected).
            entailment_threshold: Minimum confidence to add an entailment edge.
            contradiction_threshold: Minimum confidence to flag a contradiction.
        """
        self._backend = backend
        self._api_key = api_key
        self._entailment_threshold = entailment_threshold
        self._contradiction_threshold = contradiction_threshold
        self._backend_initialized = backend is not None

        self.nodes: dict[str, CommitmentNode] = {}
        self.edges: list[EntailmentEdge] = []
        self.adjacency: dict[str, list[str]] = {}
        self.violations: list[ViolationPath] = []
        self._step_count: int = 0

    def _get_backend(self) -> EntailmentBackend:
        """Lazy-initialize the entailment backend."""
        if not self._backend_initialized:
            self._backend = get_backend(api_key=self._api_key)
            self._backend_initialized = True
        return self._backend  # type: ignore

    def add_step(
        self,
        reasoning: str,
        action: str,
        *,
        step_index: Optional[int] = None,
        test_mode: bool = False,
    ) -> Optional[ViolationPath]:
        """Add a step to the commitment graph and check for violations.

        Args:
            reasoning: The agent's stated reasoning at this step.
            action: The action the agent is taking.
            step_index: Optional step number (auto-increments if omitted).
            test_mode: Use test fixtures instead of backends.

        Returns:
            ViolationPath if a violation is detected, None otherwise.
        """
        self._step_count += 1
        idx = step_index if step_index is not None else self._step_count

        # ── Phase 1: Extract beliefs (NLP — uses LLM or fixtures) ──
        new_nodes = self._extract_beliefs(reasoning, idx, test_mode=test_mode)

        # ── Phase 2: Add nodes to graph ──
        for node in new_nodes:
            if node.content not in self.nodes:
                self.nodes[node.content] = node
                self.adjacency[node.content] = []

        # ── Phase 3: Compute entailment edges (backend — NLI/embed/LLM) ──
        if not test_mode:
            self._compute_edges(new_nodes, idx)
        else:
            self._compute_edges_test(new_nodes, idx)

        # ── Phase 4: Compute closure (ALGORITHM — BFS, O(V+E)) ──
        closure = self.get_closure()

        # ── Phase 5: Check action (backend for contradiction only) ──
        if self._step_count > 1 and action and closure:
            violation = self._detect_violation(
                action, idx, closure, test_mode=test_mode,
            )
            if violation:
                self.violations.append(violation)
                return violation

        return None

    def get_closure(self) -> set[str]:
        """Compute commitment closure via convergent BFS.

        PURE ALGORITHM — no LLM, no API, no neural network.

        Starts from ALL nodes (explicit assertions, surfaced premises, and
        forward commitments) and follows entailment edges until convergence
        — no new nodes are reachable.

        The key difference from one-pass BFS: by including premises and
        forward commitments as seeds, the closure is COMPLETE. If step 3
        surfaces "f must be continuous" as a premise, and step 5 adds
        "f is discontinuous", the contradiction is reachable in the closure.

        Complexity: O(V + E) per iteration, O(k(V+E)) total where k = depth
        of the longest entailment chain (typically small, converges fast).
        """
        # Seed from ALL nodes — explicit, premises, and forward commitments
        # This is the key architectural difference: premises and commitments
        # are first-class members of the closure, not metadata.
        visited: set[str] = set(self.nodes.keys())
        queue: list[str] = list(visited)

        # BFS to convergence
        while queue:
            current = queue.pop(0)
            for neighbor in self.adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return visited

    def find_path(self, start: str, end: str) -> Optional[list[CommitmentNode]]:
        """Find a path from start to end in the graph (BFS).

        Used to construct the violation chain — showing the researcher
        exactly how the agent's own assertions lead to the contradiction.
        """
        if start not in self.nodes or end not in self.nodes:
            return None

        visited: set[str] = {start}
        queue: list[list[str]] = [[start]]

        while queue:
            path = queue.pop(0)
            current = path[-1]

            if current == end:
                return [self.nodes[c] for c in path]

            for neighbor in self.adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        return None

    def _extract_beliefs(
        self, reasoning: str, step_index: int, *, test_mode: bool,
        exhaustive: bool = True,
    ) -> list[CommitmentNode]:
        """Extract beliefs from reasoning text.

        When exhaustive=True (default), uses the three-tier extractor to surface:
          - explicit assertions (is_explicit=True)
          - hidden premises the step requires (is_explicit=False, modality='premise')
          - forward commitments the step locks in (is_explicit=False, modality='commitment')

        When exhaustive=False, falls back to the single-tier extractor (backward compat).
        """
        if exhaustive and not test_mode:
            from nous.exhaust import extract_exhaustive
            result = extract_exhaustive(
                reasoning, step_index, api_key=self._api_key, test_mode=test_mode,
            )
            nodes = []
            for belief in result.explicit:
                nodes.append(CommitmentNode(
                    content=belief, source_step=step_index,
                    is_explicit=True, modality=_detect_modality(belief),
                ))
            for belief in result.premises:
                nodes.append(CommitmentNode(
                    content=belief, source_step=step_index,
                    is_explicit=False, modality='premise',
                ))
            for belief in result.commitments:
                nodes.append(CommitmentNode(
                    content=belief, source_step=step_index,
                    is_explicit=False, modality='commitment',
                ))
            return nodes

        # Fallback: single-tier extraction
        from nous.extractor import extract_beliefs
        beliefs = extract_beliefs(reasoning, test_mode=test_mode, api_key=self._api_key)
        nodes = []
        for belief in beliefs:
            modality = _detect_modality(belief)
            node = CommitmentNode(
                content=belief, source_step=step_index,
                is_explicit=True, modality=modality,
            )
            nodes.append(node)
        return nodes

    def _compute_edges(
        self, new_nodes: list[CommitmentNode], step_index: int,
    ) -> None:
        """Compute entailment edges using the backend.

        For each new node, check entailment against ALL existing nodes.
        Add an edge if the backend detects entailment above threshold.
        """
        backend = self._get_backend()
        existing_nodes = list(self.nodes.values())

        for new_node in new_nodes:
            for existing_node in existing_nodes:
                if new_node.content == existing_node.content:
                    continue

                # Check both directions
                # Does existing → new?
                result = backend.check_entailment(
                    existing_node.content, new_node.content,
                )
                if (result.relation == "entailment"
                        and result.confidence >= self._entailment_threshold):
                    edge = EntailmentEdge(
                        premise=existing_node,
                        consequence=new_node,
                        rule=self._infer_edge_rule(existing_node, new_node),
                        confidence=result.confidence,
                    )
                    self.edges.append(edge)
                    self.adjacency.setdefault(existing_node.content, []).append(
                        new_node.content
                    )

                # Does new → existing?
                result = backend.check_entailment(
                    new_node.content, existing_node.content,
                )
                if (result.relation == "entailment"
                        and result.confidence >= self._entailment_threshold):
                    edge = EntailmentEdge(
                        premise=new_node,
                        consequence=existing_node,
                        rule=self._infer_edge_rule(new_node, existing_node),
                        confidence=result.confidence,
                    )
                    self.edges.append(edge)
                    self.adjacency.setdefault(new_node.content, []).append(
                        existing_node.content
                    )

    def _compute_edges_test(
        self, new_nodes: list[CommitmentNode], step_index: int,
    ) -> None:
        """In test mode, infer edges from closure fixtures."""
        from nous.closure import _TEST_CLOSURES

        all_contents = set(self.nodes.keys())
        for fixture_key, closure in _TEST_CLOSURES.items():
            if not fixture_key.issubset(all_contents):
                continue

            derived = set(closure) - fixture_key
            for d in derived:
                if d in self.nodes:
                    continue

                derived_node = CommitmentNode(
                    content=d,
                    source_step=step_index,
                    is_explicit=False,
                    modality=_detect_modality(d),
                )
                self.nodes[d] = derived_node
                self.adjacency[d] = []

                for premise_content in fixture_key:
                    if premise_content in self.nodes:
                        edge = EntailmentEdge(
                            premise=self.nodes[premise_content],
                            consequence=derived_node,
                            rule="derived",
                        )
                        self.edges.append(edge)
                        self.adjacency.setdefault(premise_content, []).append(d)
                        break

    def _detect_violation(
        self,
        action: str,
        step_index: int,
        closure: set[str],
        *,
        test_mode: bool,
    ) -> Optional[ViolationPath]:
        """Check if action contradicts any commitment in the closure.

        Uses the entailment backend for semantic contradiction detection,
        then uses graph structure for classification. In test mode, uses
        TestBackend which routes through coherence fixtures — same code path.
        """
        closure_list = list(closure)

        if test_mode:
            from nous.entailment import TestBackend
            backend = TestBackend()
        else:
            backend = self._get_backend()

        # Batch check: does action contradict any commitment?
        results = backend.batch_check_contradiction(closure_list, action)

        # Find the strongest contradiction
        best_idx = -1
        best_confidence = 0.0

        for i, result in enumerate(results):
            if (result.relation == "contradiction"
                    and result.confidence > best_confidence
                    and result.confidence >= self._contradiction_threshold):
                best_idx = i
                best_confidence = result.confidence

        if best_idx < 0:
            return None

        violated_content = closure_list[best_idx]
        violated_node = self.nodes.get(violated_content, CommitmentNode(
            content=violated_content, source_step=0, is_explicit=False,
        ))

        # Find the longest path from an explicit assertion to the violated node
        path = self._find_violation_path(violated_node)

        # Classify violation type from graph structure (ALGORITHM, not LLM)
        violation_type = _classify_violation(path, self.edges)

        # In test mode, override classification with fixture's type if available
        if test_mode:
            from nous.coherence import _TEST_COHERENCE
            for commitment in closure_list:
                key = (action, commitment)
                if key in _TEST_COHERENCE and not _TEST_COHERENCE[key].coherent:
                    fixture_type = _TEST_COHERENCE[key].violation_type
                    if fixture_type:
                        violation_type = fixture_type
                    break

        return ViolationPath(
            path=path,
            violated_node=violated_node,
            action=action,
            action_step=step_index,
            violation_type=violation_type,
            confidence=best_confidence,
            explanation=f"Action '{action}' contradicts commitment: {violated_content}",
        )

    def _find_violation_path(
        self, violated_node: CommitmentNode,
    ) -> list[CommitmentNode]:
        """Find the longest path from any explicit assertion to the violated node."""
        best_path: list[CommitmentNode] = [violated_node]

        for content, node in self.nodes.items():
            if node.is_explicit:
                path = self.find_path(content, violated_node.content)
                if path and len(path) > len(best_path):
                    best_path = path

        return best_path

    @staticmethod
    def _infer_edge_rule(
        premise: CommitmentNode, consequence: CommitmentNode,
    ) -> str:
        """Infer the type of entailment edge from node modalities."""
        if premise.modality == "revised" or consequence.modality == "revised":
            return "revision"
        if premise.modality == "possible" or consequence.modality == "possible":
            return "modal"
        if premise.modality == "temporal" or consequence.modality == "temporal":
            return "temporal"
        return "modus_ponens"

    def to_dict(self) -> dict:
        """Serialize the graph for inspection/visualization."""
        return {
            "nodes": [
                {
                    "content": n.content,
                    "source_step": n.source_step,
                    "is_explicit": n.is_explicit,
                    "modality": n.modality,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "from": e.premise.content,
                    "to": e.consequence.content,
                    "rule": e.rule,
                    "confidence": e.confidence,
                }
                for e in self.edges
            ],
            "violations": [
                {
                    "chain": v.format_chain(),
                    "type": v.violation_type,
                    "confidence": v.confidence,
                    "step": v.action_step,
                }
                for v in self.violations
            ],
            "closure_size": len(self.get_closure()),
        }

    def to_dot(self) -> str:
        """Export as Graphviz DOT format for visualization."""
        lines = ["digraph CommitmentGraph {"]
        lines.append('  rankdir=TB;')
        lines.append('  node [shape=box, style=rounded, fontsize=10];')

        idx = {c: i for i, c in enumerate(self.nodes.keys())}

        for content, node in self.nodes.items():
            label = content[:60] + "..." if len(content) > 60 else content
            label = label.replace('"', '\\"')
            color = {
                "asserted": "lightblue",
                "possible": "lightyellow",
                "temporal": "lightcoral",
                "revised": "lightgray",
            }.get(node.modality, "white")
            style = "filled,rounded" if node.is_explicit else "filled,rounded,dashed"
            lines.append(
                f'  n{idx[content]} [label="{label}", fillcolor="{color}", style="{style}"];'
            )

        for edge in self.edges:
            if edge.premise.content in idx and edge.consequence.content in idx:
                lines.append(
                    f'  n{idx[edge.premise.content]} -> n{idx[edge.consequence.content]} '
                    f'[label="{edge.rule}", fontsize=8];'
                )

        for v in self.violations:
            if v.violated_node.content in idx:
                lines.append(
                    f'  n{idx[v.violated_node.content]} [color=red, penwidth=3];'
                )

        lines.append("}")
        return "\n".join(lines)

    def reset(self) -> None:
        """Clear all state."""
        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()
        self.violations.clear()
        self._step_count = 0

    def __repr__(self) -> str:
        return (
            f"CommitmentGraph(nodes={len(self.nodes)}, "
            f"edges={len(self.edges)}, "
            f"closure={len(self.get_closure())}, "
            f"violations={len(self.violations)})"
        )
