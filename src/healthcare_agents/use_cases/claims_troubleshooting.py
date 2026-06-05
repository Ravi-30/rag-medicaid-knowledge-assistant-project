"""Use Case 3 — Claims & Eligibility Troubleshooting."""

import asyncio
from typing import Any

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestration import GraphOrchestrator
from healthcare_agents.orchestration.triage import triage_request
from healthcare_agents.tools.claims import get_claim_status
from healthcare_agents.tools.eligibility import verify_eligibility
from healthcare_agents.tools.provider_directory import lookup_provider
from healthcare_agents.use_cases.base import UseCaseResult


class ClaimsTroubleshootingUseCase:
    """End-to-end troubleshooting: triage → context → diagnose → resolve/escalate → audit."""

    USE_CASE_ID = "uc3_claims_troubleshooting"
    MAX_REACT_ITERATIONS = 3

    def __init__(self, orchestrator: GraphOrchestrator | None = None):
        self.orchestrator = orchestrator or GraphOrchestrator()

    async def execute(self, query: str, context: AgentContext | None = None) -> UseCaseResult:
        ctx = context or AgentContext(role="member")
        result = UseCaseResult(use_case=self.USE_CASE_ID, status="in_progress")

        # Step 1: User input & triage
        result.add_step(1, "user_input", "member", status="completed", summary=query[:200])
        triage = triage_request(query, member_id=ctx.member_id)
        result.add_step(
            1,
            "triage_routing",
            "triage_routing_agent",
            status="completed",
            summary=f"Issue type routed: {triage.primary_agent}",
            triage=triage.model_dump(),
        )

        # Step 2: Context retrieval — parallel member, claims, provider
        consolidated = await self._gather_context(ctx)
        ctx.metadata["consolidated_context"] = consolidated
        result.add_step(
            2,
            "context_retrieval",
            "memory_context_agent",
            status="completed",
            summary="Consolidated member, claims, eligibility, provider context.",
            context=consolidated,
        )

        # Step 3: Issue diagnosis — ReAct loop
        diagnosis = await self._diagnose(ctx, query)
        result.add_step(
            3,
            "issue_diagnosis",
            "knowledge_troubleshooting_agent",
            status="completed",
            summary=diagnosis.get("root_cause", "under investigation"),
            diagnosis=diagnosis,
        )

        resolution_path = diagnosis.get("resolution_path", "escalate")
        root_cause = diagnosis.get("root_cause", "unknown")

        # Step 4: Resolution & action
        if resolution_path == "auto_resolve" and ctx.metadata.get("claim_id"):
            claims = await self.orchestrator.run(
                f"Reprocess claim {ctx.metadata['claim_id']} after troubleshooting",
                agent="claims",
                context=ctx,
            )
            result.add_step(4, "auto_resolve", claims.agent_name, claims)
            result.status = "completed"
            result.final_message = (
                f"Issue diagnosed: {root_cause}.\n"
                f"Action: Claim flagged for reprocessing.\n"
                f"{claims.content}"
            )
        elif resolution_path == "needs_info":
            result.status = "needs_info"
            result.final_message = diagnosis.get(
                "clarification",
                "Please provide claim ID and date of service for further investigation.",
            )
            return result
        else:
            escalation = await self.orchestrator.run(
                query,
                agent="escalation",
                context=AgentContext(
                    member_id=ctx.member_id,
                    case_id=ctx.case_id,
                    metadata={
                        **ctx.metadata,
                        "source_agent": "claims_troubleshooting",
                        "root_cause": root_cause,
                        "confidence": diagnosis.get("confidence", 0.4),
                    },
                ),
            )
            result.add_step(4, "escalation_hitl", escalation.agent_name, escalation)
            result.status = "escalated"
            result.final_message = (
                f"Issue diagnosed: {root_cause}.\n"
                f"This case requires specialist review.\n"
                f"{escalation.content}"
            )

        # Step 5: Output & response summary
        result.add_step(
            5,
            "member_response",
            "experience_layer",
            status="completed",
            summary=result.final_message[:300],
        )

        # Step 6: Audit & observability
        ctx.metadata["action_history"] = [s.name for s in result.steps]
        ctx.metadata["trace"] = [{"name": s.name, "agent": s.agent} for s in result.steps]
        policy = await self.orchestrator.run(
            "Audit troubleshooting decision for compliance",
            agent="policy_compliance",
            context=ctx,
        )
        result.add_step(6, "audit_observability", policy.agent_name, policy)
        result.metadata["audit_logged"] = True

        # Step 7: Memory & knowledge update
        memory = await self.orchestrator.run(query, agent="memory_context", context=ctx)
        result.add_step(7, "memory_knowledge_update", memory.agent_name, memory)
        result.metadata["root_cause"] = root_cause
        result.metadata["resolution_path"] = resolution_path

        return result

    async def _gather_context(self, ctx: AgentContext) -> dict[str, Any]:
        member_id = ctx.member_id or "member-unknown"
        claim_id = ctx.metadata.get("claim_id")

        tasks = [
            verify_eligibility(member_id),
            lookup_provider(npi=ctx.metadata.get("provider_npi")),
        ]
        if claim_id:
            tasks.append(get_claim_status(claim_id))

        results = await asyncio.gather(*tasks)
        consolidated: dict[str, Any] = {
            "member": {"member_id": member_id, "eligibility": results[0]},
            "provider": results[1],
        }
        if claim_id and len(results) > 2:
            consolidated["claim"] = results[2]
        return consolidated

    async def _diagnose(self, ctx: AgentContext, query: str) -> dict[str, Any]:
        trace: list[dict[str, Any]] = []
        confidence = 0.0
        root_cause = "under review"
        resolution_path = "escalate"

        for i in range(self.MAX_REACT_ITERATIONS):
            trace.append({"iteration": i, "phase": "retrieve_reason"})

            knowledge = await self.orchestrator.run(query, agent="knowledge", context=ctx)
            trace.append({"phase": "knowledge", "confidence": knowledge.confidence})
            confidence = max(confidence, knowledge.confidence)

            if ctx.metadata.get("claim_id"):
                claims = await self.orchestrator.run(
                    f"Investigate claim {ctx.metadata['claim_id']} denial",
                    agent="claims",
                    context=ctx,
                )
                trace.append({"phase": "claims_investigation"})
                confidence = max(confidence, claims.confidence)

            eligibility = await self.orchestrator.run(
                "Verify eligibility at date of service",
                agent="eligibility",
                context=ctx,
            )
            trace.append({"phase": "eligibility_check"})

            lower = query.lower()
            if "denied" in lower or "denial" in lower:
                root_cause = "claim_denial"
                if eligibility.metadata.get("eligible") and confidence >= 0.6:
                    resolution_path = "auto_resolve"
                elif not ctx.metadata.get("claim_id"):
                    resolution_path = "needs_info"
                    break
            elif "eligib" in lower:
                root_cause = "eligibility_issue"
                resolution_path = "auto_resolve" if eligibility.metadata.get("eligible") else "escalate"
            elif confidence >= 0.75:
                root_cause = "policy_clarification"
                resolution_path = "auto_resolve"
                break

            if confidence >= 0.7:
                break

        clarification = None
        if resolution_path == "needs_info":
            clarification = "Please provide your claim ID and date of service."

        return {
            "root_cause": root_cause,
            "confidence": confidence,
            "resolution_path": resolution_path,
            "react_trace": trace,
            "clarification": clarification,
        }
