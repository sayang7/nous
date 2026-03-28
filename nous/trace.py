"""Built-in reasoning trace for auditability.

Every decision the engine makes is recorded in a structured,
queryable trace. This is what makes Nous trustworthy — you can
audit exactly why a violation was flagged or missed.

Usage:
    n = Nous()
    n.step("f is continuous on [a,b]", "Apply IVT")
    for entry in n.trace():
        print(entry)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TraceEvent(Enum):
    """Types of events in the reasoning trace."""
    STEP_START = "step_start"
    BELIEFS_EXTRACTED = "beliefs_extracted"
    NODE_ADDED = "node_added"
    EDGE_ADDED = "edge_added"
    CLOSURE_COMPUTED = "closure_computed"
    VIOLATION_CHECK = "violation_check"
    VIOLATION_FOUND = "violation_found"
    STEP_COMPLETE = "step_complete"
    HYPOTHETICAL_ENTER = "hypothetical_enter"
    HYPOTHETICAL_EXIT = "hypothetical_exit"


@dataclass
class TraceEntry:
    """A single entry in the reasoning trace."""
    event: TraceEvent
    step_index: int
    timestamp: float
    message: str
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        prefix = {
            TraceEvent.STEP_START: ">>>",
            TraceEvent.BELIEFS_EXTRACTED: "  +",
            TraceEvent.NODE_ADDED: "  ·",
            TraceEvent.EDGE_ADDED: "  →",
            TraceEvent.CLOSURE_COMPUTED: "  =",
            TraceEvent.VIOLATION_CHECK: "  ?",
            TraceEvent.VIOLATION_FOUND: "  ✗",
            TraceEvent.STEP_COMPLETE: "  ✓",
            TraceEvent.HYPOTHETICAL_ENTER: " ┌─",
            TraceEvent.HYPOTHETICAL_EXIT: " └─",
        }.get(self.event, "   ")
        return f"[step {self.step_index}] {prefix} {self.message}"


class ReasoningTrace:
    """Structured trace of every engine decision.

    Append-only log. Each entry records what happened, when,
    and why — so a researcher can audit the engine's behavior.
    """

    def __init__(self):
        self._entries: list[TraceEntry] = []
        self._current_step: int = 0

    def record(
        self,
        event: TraceEvent,
        message: str,
        step_index: Optional[int] = None,
        **details,
    ) -> None:
        """Record a trace event."""
        self._entries.append(TraceEntry(
            event=event,
            step_index=step_index or self._current_step,
            timestamp=time.time(),
            message=message,
            details=details,
        ))

    def set_step(self, step_index: int) -> None:
        """Set the current step index."""
        self._current_step = step_index

    @property
    def entries(self) -> list[TraceEntry]:
        """All trace entries."""
        return list(self._entries)

    def for_step(self, step_index: int) -> list[TraceEntry]:
        """Get all trace entries for a specific step."""
        return [e for e in self._entries if e.step_index == step_index]

    def violations_only(self) -> list[TraceEntry]:
        """Get only violation-related entries."""
        return [
            e for e in self._entries
            if e.event in (TraceEvent.VIOLATION_CHECK, TraceEvent.VIOLATION_FOUND)
        ]

    def summary(self) -> str:
        """One-line summary of the trace."""
        steps = max((e.step_index for e in self._entries), default=0)
        violations = sum(1 for e in self._entries if e.event == TraceEvent.VIOLATION_FOUND)
        nodes = sum(1 for e in self._entries if e.event == TraceEvent.NODE_ADDED)
        edges = sum(1 for e in self._entries if e.event == TraceEvent.EDGE_ADDED)
        return (
            f"{steps} steps, {nodes} nodes added, {edges} edges added, "
            f"{violations} violations found"
        )

    def clear(self) -> None:
        """Clear the trace."""
        self._entries.clear()
        self._current_step = 0

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)

    def __str__(self) -> str:
        return "\n".join(str(e) for e in self._entries)

    def __repr__(self) -> str:
        return f"ReasoningTrace({self.summary()})"
