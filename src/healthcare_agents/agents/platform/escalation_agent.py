from typing import Any
from uuid import uuid4

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.agents.reasoning import ReasoningAgent


class EscalationAgent(ReasoningAgent):
    """Escalates complex cases for human review or supervisor handoff."""

    name = "escalation_agent"
    description = (
        "You escalate complex, high-risk, or unresolved cases to human supervisors "
        "or specialized teams."
    )

    async def _act(
        self, context: AgentContext, query: str, thought: dict[str, Any]
    ) -> dict[str, Any]:
        escalation_id = f"ESC-{uuid4().hex[:8].upper()}"
        reason = context.metadata.get("escalation_reason", query[:200])
        priority = context.metadata.get("priority", "normal")
        if context.metadata.get("risk_level") == "high":
            priority = "urgent"

        content = (
            f"Escalation Created\n"
            f"Escalation ID: {escalation_id}\n"
            f"Priority: {priority}\n"
            f"Reason: {reason}\n"
            f"Status: pending_supervisor_review"
        )
        return {
            "content": content,
            "confidence": 0.9,
            "metadata": {
                "escalation_id": escalation_id,
                "priority": priority,
                "requires_hitl": True,
            },
        }
