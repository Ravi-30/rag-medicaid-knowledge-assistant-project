"""Base types for end-to-end XYZ Healthcare Corp use cases."""

from dataclasses import dataclass, field
from typing import Any

from healthcare_agents.agents.base import AgentContext, AgentResult


@dataclass
class UseCaseStep:
    step: int
    name: str
    agent: str
    status: str
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UseCaseResult:
    use_case: str
    status: str  # completed | pending_confirmation | escalated | denied | needs_info
    steps: list[UseCaseStep] = field(default_factory=list)
    final_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(
        self,
        step_num: int,
        name: str,
        agent: str,
        result: AgentResult | None = None,
        status: str = "completed",
        summary: str = "",
        **metadata: Any,
    ) -> None:
        self.steps.append(
            UseCaseStep(
                step=step_num,
                name=name,
                agent=agent,
                status=status,
                summary=summary or (result.content[:200] if result else ""),
                metadata={
                    **(result.metadata if result else {}),
                    **metadata,
                },
            )
        )
