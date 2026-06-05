from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent
from healthcare_agents.tools.authorization import check_auth_requirement, submit_prior_auth


class AuthorizationAgent(BaseAgent):
    """Manages prior authorization workflows."""

    name = "authorization_agent"
    description = (
        "You determine prior authorization requirements and submit authorization "
        "requests with supporting clinical documentation."
    )

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        member_id = context.subject_id or "member-unknown"
        procedure_code = context.metadata.get("procedure_code", "MRI")
        clinical_notes = context.clinical_notes or context.metadata.get("clinical_notes", "")

        auth_check = await check_auth_requirement(procedure_code)
        tool_calls = [{"tool": "check_auth_requirement", "result": auth_check}]

        if auth_check["requires_prior_auth"] and clinical_notes:
            submission = await submit_prior_auth(
                member_id=member_id,
                procedure_code=procedure_code,
                clinical_notes=clinical_notes,
                provider_npi=context.metadata.get("provider_npi"),
            )
            tool_calls.append({"tool": "submit_prior_auth", "result": submission})
            content = (
                f"Prior Authorization\n"
                f"Procedure: {procedure_code}\n"
                f"Required: Yes\n"
                f"Authorization ID: {submission['authorization_id']}\n"
                f"Status: {submission['status']}\n"
                f"SLA: {submission['sla_days']} days"
            )
            metadata = {
                "authorization_id": submission["authorization_id"],
                "status": submission["status"],
            }
        else:
            content = (
                f"Prior Authorization\n"
                f"Procedure: {procedure_code}\n"
                f"Required: {auth_check['requires_prior_auth']}\n"
            )
            if auth_check["requires_prior_auth"] and not clinical_notes:
                content += "Action: Clinical notes required before submission."
            metadata = {"requires_prior_auth": auth_check["requires_prior_auth"]}

        policy_snippets = "\n".join(f"- {s}" for s in context.rag_context)
        if policy_snippets:
            content += f"\n\nPolicy Context:\n{policy_snippets}"

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.85,
            tool_calls=tool_calls,
            metadata=metadata,
        )
