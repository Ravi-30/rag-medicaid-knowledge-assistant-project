from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent
from healthcare_agents.tools.eligibility import verify_eligibility


class EligibilityAgent(BaseAgent):
    """Verifies member eligibility and benefit coverage."""

    name = "eligibility_agent"
    description = (
        "You verify Medicaid and health plan eligibility, coverage status, "
        "and available benefits for members."
    )

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        member_id = context.subject_id or "member-unknown"
        result = await verify_eligibility(member_id)

        policy_snippets = "\n".join(f"- {s}" for s in context.rag_context)
        content = (
            f"Eligibility Verification\n"
            f"Member ID: {member_id}\n"
            f"Eligible: {result['eligible']}\n"
            f"Plan: {result.get('plan', 'N/A')}\n"
            f"Coverage Status: {result['coverage_status']}\n"
            f"Benefits: {result['benefits']}"
        )
        if policy_snippets:
            content += f"\n\nPolicy Context:\n{policy_snippets}"

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.9 if result["eligible"] else 0.7,
            tool_calls=[{"tool": "verify_eligibility", "result": result}],
            metadata={"eligible": result["eligible"], "plan": result.get("plan")},
        )
