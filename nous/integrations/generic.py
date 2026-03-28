"""Generic integration for any agent framework.

Works with OpenAI Agents SDK, CrewAI, AutoGPT, or any custom agent loop.

Usage:
    from nous.integrations.generic import guard_agent_loop

    # Wrap any iterable of (reasoning, action) pairs
    steps = [
        ("The API returns JSON.", "Send request."),
        ("Extract name field.", "Split by commas."),
    ]

    for step, result in guard_agent_loop(steps):
        if not result:  # StepResult is falsy when incoherent
            print(f"STOPPED: {result.violation['type']}")
            break
        print(f"Step {result.step_index}: OK")

    # Or use the decorator
    @guarded(on_violation="warn")
    def my_agent_step(reasoning, action):
        return do_something(action)
"""

from __future__ import annotations

import functools
import logging
from typing import Callable, Generator, Iterable, Optional, Tuple, Union

from nous import Nous, StepResult

logger = logging.getLogger(__name__)


def guard_agent_loop(
    steps: Iterable[Union[Tuple[str, str], dict]],
    *,
    on_violation: str = "warn",
    api_key: Optional[str] = None,
    nous: Optional[Nous] = None,
    test_mode: Optional[bool] = None,
) -> Generator[Tuple[Union[Tuple[str, str], dict], StepResult], None, None]:
    """Wrap an iterable of agent steps with Nous monitoring.

    Each step can be either:
    - A tuple of (reasoning, action)
    - A dict with 'text'/'reasoning' and 'action' keys

    Yields (original_step, StepResult) pairs.

    Example:
        for step, result in guard_agent_loop(agent.stream()):
            if not result:
                agent.stop()
                break
    """
    engine = nous or Nous(api_key=api_key)

    for step in steps:
        if isinstance(step, dict):
            reasoning = step.get("text") or step.get("reasoning", "")
            action = step.get("action", "")
        else:
            reasoning, action = step

        result = engine.step(reasoning, action, test_mode=test_mode)
        yield step, result

        if not result.coherent and on_violation == "halt":
            return


def guarded(
    *,
    on_violation: str = "warn",
    api_key: Optional[str] = None,
    test_mode: Optional[bool] = None,
    _nous: Optional[Nous] = None,
) -> Callable:
    """Decorator that guards an agent step function with Nous.

    The decorated function must accept (reasoning: str, action: str) as
    its first two arguments. Nous checks each call incrementally.

    Example:
        @guarded(on_violation="halt")
        def agent_step(reasoning, action):
            return execute(action)

        # Each call is monitored. Raises NousViolationError on halt.
        agent_step("The API returns JSON.", "Send request.")
        agent_step("Extract name.", "Split by commas.")  # May raise!
    """
    engine = _nous or Nous(api_key=api_key)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(reasoning: str, action: str, *args, **kwargs):
            result = engine.step(reasoning, action, test_mode=test_mode)
            if not result.coherent and on_violation == "halt":
                raise NousViolationError(
                    f"Nous HALT: {result.violation['type']} "
                    f"at step {result.step_index}",
                    violation=result.violation,
                )
            return func(reasoning, action, *args, **kwargs)

        wrapper.nous = engine  # type: ignore[attr-defined]
        return wrapper

    return decorator


class NousViolationError(Exception):
    """Raised when Nous halts an agent due to a violation."""

    def __init__(self, message: str, violation: dict = None):
        super().__init__(message)
        self.violation = violation


# Backward compatibility
ClosureViolationError = NousViolationError
