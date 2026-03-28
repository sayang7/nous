"""LangChain integration for Nous.

Drop-in callback handler that monitors any LangChain agent for
reasoning violations in real-time.

Usage:
    from langchain.agents import AgentExecutor
    from nous.integrations.langchain import NousCallback

    callback = NousCallback(on_violation="halt")
    agent = AgentExecutor(agent=..., tools=..., callbacks=[callback])
    result = agent.invoke({"input": "..."})

    # Check what happened
    print(callback.nous)              # Nous(commitments=..., violations=...)
    for v in callback.nous.violations:
        print(f"{v['type']} at step {v['step']}")
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from nous import Nous

logger = logging.getLogger(__name__)

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    # Provide a stub so the module can be imported without langchain
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Stub for when langchain is not installed."""
        pass


class NousCallback(BaseCallbackHandler):
    """LangChain callback that monitors agent reasoning with Nous.

    Intercepts agent reasoning (on_agent_action) and tool outputs
    (on_tool_end) to build a trace, then checks each step for
    reasoning violations.

    Args:
        on_violation: "halt", "warn", or "log".
            When "halt", raises NousViolationError to stop the agent.
        api_key: API key for Nous analysis.
        nous: Optional pre-configured Nous instance.
    """

    def __init__(
        self,
        *,
        on_violation: str = "warn",
        api_key: Optional[str] = None,
        nous: Optional[Nous] = None,
    ):
        super().__init__()
        self.nous = nous or Nous(api_key=api_key)
        self.on_violation = on_violation
        self._last_reasoning: str = ""
        self._step_count: int = 0

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        """Called when the agent decides on an action."""
        reasoning = ""
        if hasattr(action, "log"):
            reasoning = action.log
        elif hasattr(action, "message_log"):
            for msg in action.message_log:
                if hasattr(msg, "content"):
                    reasoning += str(msg.content) + " "

        action_str = ""
        if hasattr(action, "tool"):
            action_str = f"{action.tool}: {action.tool_input}"
        elif hasattr(action, "return_values"):
            action_str = str(action.return_values)

        if reasoning and action_str:
            self._step_count += 1
            result = self.nous.step(reasoning, action_str)

            if not result.coherent and self.on_violation == "halt":
                from nous.integrations.generic import NousViolationError
                raise NousViolationError(
                    f"Nous HALT: {result.violation['type']} "
                    f"at step {result.step_index}",
                    violation=result.violation,
                )
            elif not result.coherent and self.on_violation == "warn":
                logger.warning(
                    "Nous violation: %s at step %d",
                    result.violation.get("type", "unknown"),
                    result.step_index,
                )

        self._last_reasoning = reasoning

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool finishes. Updates reasoning context."""
        if output:
            self._last_reasoning = output

    def on_chain_end(self, outputs: Any, **kwargs: Any) -> None:
        """Called when the agent chain ends. Log summary."""
        violations = self.nous.violations
        if violations:
            logger.warning(
                "Nous summary: %d violation(s) across %d steps",
                len(violations),
                self._step_count,
            )


# Backward compatibility
ClosureGuardCallback = NousCallback
