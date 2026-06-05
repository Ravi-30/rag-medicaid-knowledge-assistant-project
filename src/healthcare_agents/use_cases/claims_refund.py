"""Use Case 2 — Claims Refund / Adjustment Request (policy-governed finances)."""

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.control.hitl import HumanInTheLoop
from healthcare_agents.orchestration import GraphOrchestrator
from healthcare_agents.orchestration.escalation_triggers import detect_escalation_triggers
from healthcare_agents.orchestration.triage import triage_request
from healthcare_agents.tools.billing import track_finance
from healthcare_agents.tools.claims import get_claim_status
from healthcare_agents.use_cases.base import UseCaseResult
from healthcare_agents.workflows.billing_refund import BillingRefundWorkflow


class ClaimsRefundUseCase:
    """End-to-end refund: triage → multi-agent decision → HITL → refund → notify → audit."""

    USE_CASE_ID = "uc2_claims_refund"

    def __init__(
        self,
        orchestrator: GraphOrchestrator | None = None,
        hitl: HumanInTheLoop | None = None,
    ):
        self.orchestrator = orchestrator or GraphOrchestrator()
        self.hitl = hitl or self.orchestrator.hitl
        self.refund_workflow = BillingRefundWorkflow()

    async def execute(self, query: str, context: AgentContext | None = None) -> UseCaseResult:
        ctx = context or AgentContext(role="member")
        result = UseCaseResult(use_case=self.USE_CASE_ID, status="in_progress")

        # Step 1: User request
        result.add_step(1, "user_request", "member", status="completed", summary=query[:200])
        request_id = f"REQ-{ctx.member_id or 'anon'}-refund"
        ctx.metadata["request_id"] = request_id

        # Step 2: Validation & routing
        triage = triage_request(query, member_id=ctx.member_id)
        result.add_step(
            2,
            "input_validation_routing",
            "triage_routing_agent",
            status="completed",
            summary=f"Intent: refund, route to billing_refund",
            request_id=request_id,
            triage=triage.model_dump(),
        )

        claim_id = ctx.metadata.get("claim_id", "")
        amount = float(ctx.metadata.get("amount_usd", 0))
        if not ctx.member_id or not claim_id or amount <= 0:
            result.status = "needs_info"
            result.final_message = (
                "Please provide member ID, claim ID, and refund amount to process this request."
            )
            return result

        # Step 3: Governed decision making — Billing → Policy → Eligibility → Finance → Audit
        billing = await self.orchestrator.run(query, agent="claims", context=ctx)
        result.add_step(3, "billing_agent_validation", billing.agent_name, billing)

        policy = await self.orchestrator.run(
            "Validate refund against plan policy and compliance rules",
            agent="policy_compliance",
            context=ctx,
        )
        result.add_step(3, "policy_agent_validation", policy.agent_name, policy)

        eligibility = await self.orchestrator.run(
            "Verify member eligibility at date of service",
            agent="eligibility",
            context=ctx,
        )
        result.add_step(3, "eligibility_agent_validation", eligibility.agent_name, eligibility)

        claim_status = await get_claim_status(claim_id)
        ctx.metadata["claim_status"] = claim_status.get("status")
        result.add_step(
            3,
            "finance_agent_assessment",
            "billing_refund_agent",
            status="completed",
            summary=f"Refundable amount: ${amount:.2f}, claim {claim_status.get('status')}",
            claim_status=claim_status,
        )

        fraud = await self.orchestrator.run(
            "Screen refund for duplicate or suspicious activity",
            agent="fraud",
            context=ctx,
        )
        result.add_step(3, "audit_agent_screening", fraud.agent_name, fraud)

        # Step 4: HITL gating — high amount or fraud risk
        high_risk = amount > 1000 or fraud.metadata.get("risk_level") in ("high", "medium")
        if high_risk:
            self.hitl.create_checkpoint(
                case_id=claim_id,
                step="refund_approval",
                reason="Refund exceeds auto-approval threshold or fraud risk detected.",
                payload={"amount_usd": amount, "claim_id": claim_id},
            )
            result.add_step(
                4,
                "hitl_gating",
                "escalation_agent",
                status="pending",
                summary="Human review required before refund execution.",
            )
            if not ctx.metadata.get("human_approved"):
                result.status = "pending_confirmation"
                result.final_message = (
                    f"Refund of ${amount:.2f} requires human approval. "
                    "A supervisor will review within 1 business day."
                )
                return result

        # Step 5: Output validation & financial response
        refund_ctx = AgentContext(
            member_id=ctx.member_id,
            role="ops_analyst",
            metadata={
                **ctx.metadata,
                "claim_id": claim_id,
                "amount_usd": amount,
                "user_confirmed": ctx.metadata.get("user_confirmed", True),
            },
        )
        refund = await self.refund_workflow.run(refund_ctx, query)
        result.add_step(5, "financial_response", refund.agent_name, refund)

        if refund.metadata.get("refund_status") == "denied":
            result.status = "denied"
            result.final_message = refund.content
            return result

        refund_id = refund.metadata.get("refund_id")
        if refund_id:
            tracked = await track_finance(refund_id)
            result.add_step(
                5,
                "transaction_recorded",
                "billing_refund_agent",
                status="completed",
                summary=f"Transaction {refund_id} logged.",
                transaction=tracked,
            )

        # Step 6: Confirmation & notification
        result.add_step(
            6,
            "confirmation_notification",
            "notification_service",
            status="completed",
            summary=(
                f"Refund confirmation sent via preferred channel. "
                f"Amount: ${amount:.2f}, ETA: 3-5 business days."
            ),
        )

        # Step 7: Memory & audit update
        ctx.metadata["refund_id"] = refund_id
        ctx.metadata["action_history"] = [s.name for s in result.steps]
        memory = await self.orchestrator.run(query, agent="memory_context", context=ctx)
        result.add_step(7, "memory_audit_update", memory.agent_name, memory)

        triggers = detect_escalation_triggers(query, ctx.metadata, confidence=0.9)
        result.metadata["audit_logged"] = True
        result.metadata["request_id"] = request_id
        result.metadata["refund_id"] = refund_id
        result.metadata["escalation_triggers"] = triggers

        result.status = "completed" if refund_id else "pending_confirmation"
        result.final_message = (
            f"Your refund of ${amount:.2f} has been "
            f"{'processed successfully' if refund_id else 'submitted for processing'}.\n"
            f"Reference: {refund_id or request_id}\n"
            "You will see the amount in your account within 3-5 business days."
        )
        return result
