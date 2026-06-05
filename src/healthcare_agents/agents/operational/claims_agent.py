from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent
from healthcare_agents.tools.claims import get_claim_status, submit_claim


class ClaimsAgent(BaseAgent):
    """Processes and validates healthcare claims."""

    name = "claims_agent"
    description = (
        "You validate claim data, submit claims for adjudication, "
        "and track claim status across the lifecycle."
    )

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        member_id = context.subject_id or "member-unknown"
        claim_id = context.metadata.get("claim_id")

        if claim_id:
            status = await get_claim_status(claim_id)
            content = (
                f"Claim Status\n"
                f"Claim ID: {status['claim_id']}\n"
                f"Status: {status['status']}\n"
                f"Notes: {status['adjudication_notes']}"
            )
            return AgentResult(
                agent_name=self.name,
                content=content,
                confidence=0.9,
                tool_calls=[{"tool": "get_claim_status", "result": status}],
                metadata={"claim_id": claim_id, "status": status["status"]},
            )

        provider_npi = context.metadata.get("provider_npi", "1234567890")
        procedure_codes = context.metadata.get("procedure_codes", ["99213"])
        submission = await submit_claim(
            member_id=member_id,
            provider_npi=provider_npi,
            procedure_codes=procedure_codes,
            service_date=context.metadata.get("service_date"),
        )

        content = (
            f"Claim Submission\n"
            f"Claim ID: {submission['claim_id']}\n"
            f"Status: {submission['status']}\n"
            f"Member: {submission['member_id']}\n"
            f"Provider NPI: {submission['provider_npi']}\n"
            f"Procedures: {', '.join(submission['procedure_codes'])}"
        )
        policy_snippets = "\n".join(f"- {s}" for s in context.rag_context)
        if policy_snippets:
            content += f"\n\nPolicy Context:\n{policy_snippets}"

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.88,
            tool_calls=[{"tool": "submit_claim", "result": submission}],
            metadata={"claim_id": submission["claim_id"], "status": submission["status"]},
        )
