from typing import Any

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.agents.reasoning import ReasoningAgent
from healthcare_agents.tools.mcp.registry import MCPToolRegistry


class MemberSupportAgent(ReasoningAgent):
    """Handles member-facing support inquiries and account questions."""

    name = "member_support_agent"
    description = "You assist members with account questions, case status, and general support."

    def __init__(self, llm_client=None, tool_registry: MCPToolRegistry | None = None):
        super().__init__(llm_client)
        self.tools = tool_registry or MCPToolRegistry()

    async def _act(
        self, context: AgentContext, query: str, thought: dict[str, Any]
    ) -> dict[str, Any]:
        member_id = context.subject_id or "member-unknown"
        tool_calls = []

        profile = await self.tools.invoke("get_profile", {"member_id": member_id})
        tool_calls.append({"tool": "get_profile", "success": profile.success})

        if profile.success:
            data = profile.data
            content = (
                f"Member Support\n"
                f"Member ID: {member_id}\n"
                f"Coverage: {data.get('coverage_status', 'unknown')}\n"
                f"Plan: {data.get('plan', 'N/A')}\n"
                f"How can I help with: {query[:100]}?"
            )
            confidence = 0.85
        else:
            content = f"Member Support\nUnable to retrieve profile for {member_id}."
            confidence = 0.5

        return {
            "content": content,
            "confidence": confidence,
            "tool_calls": tool_calls,
            "metadata": {"member_id": member_id},
        }
