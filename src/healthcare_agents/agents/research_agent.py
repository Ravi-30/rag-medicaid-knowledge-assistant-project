from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent
from healthcare_agents.tools.medical_knowledge import lookup_drug_interactions, search_literature


class ResearchAgent(BaseAgent):
    """Queries medical literature and drug databases to support clinical questions."""

    name = "research_agent"
    description = (
        "You search medical literature and drug databases to answer "
        "clinical research questions with cited, evidence-based information."
    )

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        tool_calls: list[dict] = []
        findings: list[str] = []

        if "interaction" in query.lower() or "drug" in query.lower():
            result = lookup_drug_interactions(query)
            tool_calls.append({"tool": "drug_interactions", "query": query})
            findings.append(result)

        literature = search_literature(query)
        tool_calls.append({"tool": "literature_search", "query": query})
        findings.append(literature)

        content = "\n\n".join(findings)

        if self.llm_client:
            content = await self.llm_client.chat(
                system=self._build_system_prompt(),
                user=f"Research query: {query}\n\nRaw findings:\n{content}\n\nSynthesize into a clear answer.",
            )

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.7,
            tool_calls=tool_calls,
        )
