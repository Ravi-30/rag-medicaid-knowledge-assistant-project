from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent


class PolicyComplianceAgent(BaseAgent):
    """Provides policy guidance and compliance checks."""

    name = "policy_compliance_agent"
    description = (
        "You interpret healthcare policies, verify compliance requirements, "
        "and flag fraud or regulatory risks in operational requests."
    )

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        policy_context = context.rag_context or [
            "No policy documents retrieved. Use RAG engine for grounded guidance."
        ]
        risk_flags: list[str] = []
        lower = query.lower()

        if any(kw in lower for kw in ("fraud", "duplicate", "suspicious")):
            risk_flags.append("Potential fraud investigation required.")
        if any(kw in lower for kw in ("hipaa", "phi", "unauthorized")):
            risk_flags.append("Compliance review recommended for PHI handling.")

        content = (
            "Policy & Compliance Guidance\n"
            + "\n".join(f"- {snippet}" for snippet in policy_context)
        )
        if risk_flags:
            content += "\n\nRisk Flags:\n" + "\n".join(f"- {flag}" for flag in risk_flags)

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.8,
            metadata={"risk_flags": risk_flags, "policy_sources": len(policy_context)},
        )
