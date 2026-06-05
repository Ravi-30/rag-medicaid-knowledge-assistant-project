"""Workflow evaluation — completion and branching correctness."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowEvalMetrics:
    successful_completion: bool = False
    correct_branching: bool = False
    expected_agent: str | None = None
    actual_agent: str | None = None
    steps_completed: list[str] = field(default_factory=list)
    escalation_triggered: bool = False
    policy_blocked: bool = False
    tool_success_rate: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


def _extract_agent(steps_completed: list[str]) -> str | None:
    for step in steps_completed:
        if step.startswith("execute:"):
            return step.removeprefix("execute:")
    return None


def evaluate_branching(
    steps_completed: list[str],
    expected_agent: str | None,
    evaluation_events: list[dict[str, Any]] | None = None,
) -> bool:
    """Return True when routing and execution follow the expected branch."""
    if not expected_agent:
        return True

    actual = _extract_agent(steps_completed)
    if actual == expected_agent:
        return True

    events = evaluation_events or []
    for event in events:
        if event.get("event_type") != "execution_result":
            continue
        payload = event.get("payload", {})
        if payload.get("agent") == expected_agent and payload.get("success", False):
            return True

    return False


def evaluate_workflow(
    *,
    agent_result: dict[str, Any] | None,
    steps_completed: list[str],
    metadata: dict[str, Any],
    expected_agent: str | None = None,
    evaluation_events: list[dict[str, Any]] | None = None,
) -> WorkflowEvalMetrics:
    tool_calls = (agent_result or {}).get("tool_calls", [])
    successes = sum(1 for t in tool_calls if t.get("success", True))
    total = len(tool_calls) or 1

    blocked = metadata.get("blocked", False) or metadata.get("policy_blocked", False)
    successful = agent_result is not None and not blocked
    actual_agent = _extract_agent(steps_completed)

    return WorkflowEvalMetrics(
        successful_completion=successful,
        correct_branching=evaluate_branching(steps_completed, expected_agent, evaluation_events),
        expected_agent=expected_agent,
        actual_agent=actual_agent,
        steps_completed=steps_completed,
        escalation_triggered=metadata.get("escalate", False) or metadata.get("requires_hitl", False),
        policy_blocked=blocked,
        tool_success_rate=successes / total,
        details={
            "status": metadata.get("status"),
            "resolved": metadata.get("resolved"),
        },
    )
