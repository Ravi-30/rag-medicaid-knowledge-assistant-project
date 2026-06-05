"""Use Case 1 — Healthcare Appointment Booking (10-step workflow)."""

import asyncio
from typing import Any

from healthcare_agents.agents.base import AgentContext, AgentResult
from healthcare_agents.context.pipeline import ContextEngineeringPipeline
from healthcare_agents.orchestration import GraphOrchestrator
from healthcare_agents.orchestration.triage import triage_request
from healthcare_agents.tools.eligibility import verify_eligibility
from healthcare_agents.tools.provider_directory import lookup_provider
from healthcare_agents.tools.scheduling import check_availability
from healthcare_agents.use_cases.base import UseCaseResult
from healthcare_agents.workflows.service_appointment import ServiceAppointmentWorkflow


class AppointmentBookingUseCase:
    """End-to-end appointment booking: triage → enrich → plan → confirm → book → memory."""

    USE_CASE_ID = "uc1_appointment_booking"

    def __init__(self, orchestrator: GraphOrchestrator | None = None):
        self.orchestrator = orchestrator or GraphOrchestrator()
        self.appointment = ServiceAppointmentWorkflow()
        self.context_pipeline = ContextEngineeringPipeline()

    async def execute(self, query: str, context: AgentContext | None = None) -> UseCaseResult:
        ctx = context or AgentContext(role="member")
        result = UseCaseResult(use_case=self.USE_CASE_ID, status="in_progress")

        # Step 1: User input captured
        result.add_step(1, "user_input", "member", status="completed", summary=query[:200])

        # Step 2: Triage & routing
        triage = triage_request(query, member_id=ctx.member_id)
        ctx.metadata["priority"] = triage.priority
        result.add_step(
            2,
            "triage_routing",
            "triage_routing_agent",
            status="completed",
            summary=f"Route to {triage.primary_agent}, priority {triage.priority}",
            routed_agent=triage.primary_agent,
            triage=triage.model_dump(),
        )
        if triage.needs_clarification:
            result.status = "needs_info"
            result.final_message = triage.clarification_prompt or "More information required."
            return result

        # Step 3: Knowledge — care appropriateness
        knowledge = await self.orchestrator.run(query, agent="knowledge", context=ctx)
        result.add_step(3, "knowledge_troubleshooting", knowledge.agent_name, knowledge)

        # Step 4–5: Context enrichment
        enriched = self.context_pipeline.run(
            ctx.rag_context,
            ctx.metadata.get("knowledge_graph"),
            query=query,
        )
        ctx.rag_context = enriched.snippets
        ctx.metadata["enriched_context"] = enriched.structured
        result.add_step(
            5,
            "context_enrichment",
            "memory_context_agent",
            status="completed",
            summary=f"Context artifact ({enriched.token_estimate} tokens est.)",
            sources=enriched.sources,
        )

        # Step 6–7: Parallel planning — eligibility, provider, availability, policy
        parallel = await self._parallel_planning(ctx, query)
        result.add_step(
            6,
            "service_agent_planning",
            "service_appointment_agent",
            status="completed",
            summary="Parallel: eligibility, provider, availability, policy",
            parallel_results=parallel,
        )

        if not parallel.get("eligible"):
            result.status = "denied"
            result.final_message = "Member is not eligible for scheduling under current plan."
            return result

        # Step 8: Experience — present slots / await confirmation
        appt_ctx = AgentContext(
            member_id=ctx.member_id,
            session_id=ctx.session_id,
            role=ctx.role,
            metadata={
                **ctx.metadata,
                "service_type": ctx.metadata.get("service_type", "primary_care"),
                "provider_npi": parallel.get("provider_npi"),
                "available_slots": parallel.get("available_slots", []),
                "user_confirmed": ctx.metadata.get("user_confirmed", False),
                "selected_slot": ctx.metadata.get("selected_slot"),
            },
        )
        booking = await self.appointment.run(appt_ctx, query)

        if booking.metadata.get("needs_confirmation"):
            result.add_step(8, "experience_confirmation", booking.agent_name, booking, status="pending")
            result.status = "pending_confirmation"
            result.final_message = booking.content
            result.metadata["available_slots"] = booking.metadata.get("available_slots")
            return result

        # Step 9: Policy gating passed — booking executed
        policy = await self.orchestrator.run(
            "Validate appointment booking policy compliance",
            agent="policy_compliance",
            context=ctx,
        )
        result.add_step(9, "confirmation_policy_gating", policy.agent_name, policy)
        result.add_step(9, "booking_confirmed", booking.agent_name, booking)

        # Step 10: Memory update
        memory = await self.orchestrator.run(query, agent="memory_context", context=ctx)
        result.add_step(10, "memory_update", memory.agent_name, memory)

        result.status = "completed"
        appt_id = booking.metadata.get("appointment_id", "pending")
        result.final_message = (
            f"Appointment confirmed.\n"
            f"Reference: {appt_id}\n"
            f"Provider NPI: {parallel.get('provider_npi', 'N/A')}\n"
            f"{booking.content}"
        )
        result.metadata["appointment_id"] = appt_id
        return result

    async def _parallel_planning(self, ctx: AgentContext, query: str) -> dict[str, Any]:
        member_id = ctx.member_id or "member-unknown"
        service_type = ctx.metadata.get("service_type", "primary_care")

        eligibility_task = verify_eligibility(member_id)
        provider_task = lookup_provider(npi=ctx.metadata.get("provider_npi"))
        availability_task = check_availability(member_id, service_type)
        policy_task = self.orchestrator.run(
            "Check network and referral policy for appointment",
            agent="policy_compliance",
            context=ctx,
        )

        eligibility, provider, availability, policy = await asyncio.gather(
            eligibility_task, provider_task, availability_task, policy_task
        )

        auth_needed = service_type in ("specialist_referral", "diagnostic_imaging")
        auth_result: AgentResult | None = None
        if auth_needed:
            auth_result = await self.orchestrator.run(
                f"Check prior auth requirement for {service_type}",
                agent="authorization",
                context=ctx,
            )

        return {
            "eligible": eligibility.get("eligible", False),
            "plan": eligibility.get("plan"),
            "provider_npi": provider.get("npi"),
            "provider_name": provider.get("name"),
            "network_status": provider.get("network_status"),
            "available_slots": availability.get("available_slots", []),
            "policy_compliant": "risk_flags" not in (policy.metadata or {}),
            "authorization": auth_result.metadata if auth_result else None,
        }
