"""Evaluation metrics hooks (DeepEval-style agent metrics)."""

from dataclasses import dataclass, field
from typing import Any

from healthcare_agents.evaluation.workflow_metrics import evaluate_workflow


@dataclass
class WorkflowMetrics:
    task_completed: bool = False
    successful_completion: bool = False
    correct_branching: bool = True
    tool_success_rate: float = 0.0
    escalation_triggered: bool = False
    policy_blocked: bool = False
    steps: list[str] = field(default_factory=list)
    expected_agent: str | None = None
    actual_agent: str | None = None


class MetricsCollector:
    """Collects agent workflow metrics for continuous evaluation."""

    def evaluate_run(
        self,
        agent_result: dict[str, Any] | None,
        steps_completed: list[str],
        metadata: dict[str, Any],
        evaluation_events: list[dict[str, Any]] | None = None,
        expected_agent: str | None = None,
    ) -> WorkflowMetrics:
        workflow = evaluate_workflow(
            agent_result=agent_result,
            steps_completed=steps_completed,
            metadata=metadata,
            expected_agent=expected_agent,
            evaluation_events=evaluation_events,
        )

        return WorkflowMetrics(
            task_completed=workflow.successful_completion,
            successful_completion=workflow.successful_completion,
            correct_branching=workflow.correct_branching,
            tool_success_rate=workflow.tool_success_rate,
            escalation_triggered=workflow.escalation_triggered,
            policy_blocked=workflow.policy_blocked,
            steps=workflow.steps_completed,
            expected_agent=workflow.expected_agent,
            actual_agent=workflow.actual_agent,
        )

    def to_dict(self, metrics: WorkflowMetrics) -> dict[str, Any]:
        return {
            "task_completed": metrics.task_completed,
            "successful_completion": metrics.successful_completion,
            "correct_branching": metrics.correct_branching,
            "tool_success_rate": metrics.tool_success_rate,
            "escalation_triggered": metrics.escalation_triggered,
            "policy_blocked": metrics.policy_blocked,
            "steps": metrics.steps,
            "expected_agent": metrics.expected_agent,
            "actual_agent": metrics.actual_agent,
        }
