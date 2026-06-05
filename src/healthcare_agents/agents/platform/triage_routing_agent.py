from typing import Any

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.agents.reasoning import ReasoningAgent
from healthcare_agents.orchestration.triage import triage_request


class TriageRoutingAgent(ReasoningAgent):
    """Triage & Routing — classification, ReAct routing, multi-intent, escalation."""

    name = "triage_routing_agent"
    description = (
        "You convert raw user input into structured intent, enrich context, "
        "and route to the correct downstream healthcare workflow."
    )

    async def _validate(
        self, context: AgentContext, query: str, thought: dict[str, Any]
    ) -> dict[str, Any]:
        return {"allowed": True, "reason": "Routing does not require member ID."}

    async def _act(
        self, context: AgentContext, query: str, thought: dict[str, Any]
    ) -> dict[str, Any]:
        clarification_count = int(context.metadata.get("clarification_count", 0))
        result = triage_request(
            query,
            member_id=context.subject_id,
            clarification_count=clarification_count,
        )

        if result.needs_clarification:
            content = f"Triage & Routing\n{result.clarification_prompt}"
        elif result.escalate:
            content = f"Triage & Routing\nEscalating to human agent.\n{result.explanation}"
        else:
            targets = ", ".join(result.target_agents)
            content = (
                f"Triage & Routing\n"
                f"Primary Agent: {result.primary_agent}\n"
                f"Target Agents: {targets}\n"
                f"Priority: {result.priority}\n"
                f"Confidence: {result.confidence:.0%}\n"
                f"Explanation: {result.explanation}"
            )

        return {
            "content": content,
            "confidence": result.confidence,
            "metadata": {
                "routed_agent": result.primary_agent,
                "target_agents": result.target_agents,
                "priority": result.priority,
                "needs_clarification": result.needs_clarification,
                "escalate": result.escalate,
                "triage": result.model_dump(),
            },
        }
