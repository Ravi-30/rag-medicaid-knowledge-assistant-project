from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent
from healthcare_agents.tools.provider_directory import coordinate_referral, lookup_provider


class ProviderAgent(BaseAgent):
    """Handles provider lookup and care coordination."""

    name = "provider_agent"
    description = (
        "You look up providers in the network, verify credentials, "
        "and coordinate referrals between providers."
    )

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        member_id = context.subject_id or "member-unknown"
        npi = context.metadata.get("provider_npi")
        specialty = context.metadata.get("specialty")

        if specialty and npi:
            referral = await coordinate_referral(
                member_id=member_id,
                from_provider_npi=npi,
                to_specialty=specialty,
            )
            content = (
                f"Provider Coordination\n"
                f"Referral ID: {referral['referral_id']}\n"
                f"Specialty: {referral['to_specialty']}\n"
                f"Status: {referral['status']}"
            )
            return AgentResult(
                agent_name=self.name,
                content=content,
                confidence=0.87,
                tool_calls=[{"tool": "coordinate_referral", "result": referral}],
                metadata={"referral_id": referral["referral_id"]},
            )

        provider = await lookup_provider(npi=npi, name=context.metadata.get("provider_name"))
        content = (
            f"Provider Lookup\n"
            f"Name: {provider['name']}\n"
            f"NPI: {provider['npi']}\n"
            f"Specialty: {provider['specialty']}\n"
            f"Network: {provider['network_status']}\n"
            f"Accepting Patients: {provider['accepting_new_patients']}"
        )
        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.9,
            tool_calls=[{"tool": "lookup_provider", "result": provider}],
            metadata={"provider_id": provider["provider_id"]},
        )
