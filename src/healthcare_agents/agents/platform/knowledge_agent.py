from typing import Any

from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent
from healthcare_agents.context.rag import RAGEngine
from healthcare_agents.tools.mcp.registry import MCPToolRegistry


class KnowledgeTroubleshootingAgent(BaseAgent):
    """Knowledge & Troubleshooting — iterative ReAct diagnosis loop."""

    name = "knowledge_troubleshooting_agent"
    description = (
        "You diagnose issues through iterative retrieval, reasoning, tool use, "
        "and reflection until resolved or clarification is needed."
    )
    MAX_ITERATIONS = 3
    RESOLVE_THRESHOLD = 0.75

    def __init__(
        self,
        llm_client=None,
        rag: RAGEngine | None = None,
        tools: MCPToolRegistry | None = None,
    ):
        super().__init__(llm_client)
        self.rag = rag or RAGEngine()
        self.tools = tools or MCPToolRegistry()

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        trace: list[dict[str, Any]] = []
        snippets = list(context.rag_context)
        confidence = 0.0
        tool_calls: list[dict[str, Any]] = []
        status = "partial"

        for iteration in range(self.MAX_ITERATIONS):
            trace.append({"phase": "think", "iteration": iteration, "goal": query})

            if not snippets:
                docs = await self.rag.retrieve(query, top_k=3)
                snippets = [f"{d.source}: {d.content}" for d in docs]
                trace.append({"phase": "retrieve", "count": len(snippets)})

            confidence = min(0.95, 0.4 + len(snippets) * 0.15 + iteration * 0.05)
            trace.append({"phase": "reason", "confidence": confidence})

            if context.subject_id and iteration == 1:
                profile = await self.tools.invoke("get_profile", {"member_id": context.subject_id})
                tool_calls.append({"tool": "get_profile", "success": profile.success})
                if profile.success:
                    snippets.append(f"member_profile: plan={profile.data.get('plan')}")
                    confidence = min(0.95, confidence + 0.1)

            trace.append({"phase": "reflect", "confidence": confidence})

            if confidence >= self.RESOLVE_THRESHOLD:
                status = "resolved"
                break

        if confidence < 0.5:
            content = (
                "Knowledge & Troubleshooting\n"
                "I need more information to diagnose this issue.\n"
                "Please provide: member ID, specific error or policy topic, and any claim/case ID."
            )
            status = "needs_clarification"
        elif status == "resolved":
            content = "Knowledge & Troubleshooting — Diagnosis\n" + "\n".join(
                f"- {s}" for s in snippets[:5]
            )
            content += "\n\nRecommended: Review cited policies and follow operational SOP."
        else:
            content = "Knowledge & Troubleshooting — Partial Answer\n" + "\n".join(
                f"- {s}" for s in snippets[:3]
            )

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=confidence,
            tool_calls=tool_calls,
            metadata={
                "react_trace": trace,
                "status": status,
                "sources": len(snippets),
            },
        )
