"""Policy-governed billing & refund workflow (LangGraph-style)."""

from dataclasses import dataclass, field
from typing import Any

from healthcare_agents.agents.base import AgentContext, AgentResult
from healthcare_agents.tools.billing import check_refund_eligibility, process_refund, track_finance


@dataclass
class RefundWorkflowState:
    member_id: str
    claim_id: str
    amount_usd: float
    user_confirmed: bool = False
    steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BillingRefundWorkflow:
    """Billing & Refund Agent — verify before acting, consent-gated execution."""

    name = "billing_refund_agent"

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        member_id = context.subject_id or ""
        claim_id = context.metadata.get("claim_id", "")
        amount = float(context.metadata.get("amount_usd", 0))

        if not member_id or not claim_id:
            return AgentResult(
                agent_name=self.name,
                content="Member ID and claim ID are required for refund processing.",
                confidence=0.0,
                metadata={"needs_clarification": True},
            )

        state = RefundWorkflowState(
            member_id=member_id,
            claim_id=claim_id,
            amount_usd=amount,
            user_confirmed=context.metadata.get("user_confirmed", False),
        )

        state = await self._policy_shield(state)
        state = await self._gather_context(state)
        state = await self._check_eligibility(state)
        state = await self._request_consent(state)
        state = await self._execute_refund(state)
        state = await self._track_finance(state)

        content = (
            f"Billing & Refund\n"
            f"Claim: {state.claim_id}\n"
            f"Amount: ${state.amount_usd:.2f}\n"
            f"Status: {state.metadata.get('refund_status', 'pending')}\n"
            f"Steps: {' → '.join(state.steps)}"
        )
        if state.metadata.get("refund_id"):
            content += f"\nRefund ID: {state.metadata['refund_id']}"

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.92 if state.metadata.get("refund_id") else 0.75,
            tool_calls=state.metadata.get("tool_calls", []),
            metadata={**state.metadata, "workflow_steps": state.steps},
        )

    async def _policy_shield(self, state: RefundWorkflowState) -> RefundWorkflowState:
        state.steps.append("policy_shield")
        state.metadata["pii_minimized"] = True
        state.metadata["policy_mode"] = "shield"
        return state

    async def _gather_context(self, state: RefundWorkflowState) -> RefundWorkflowState:
        state.steps.append("gather_context")
        state.metadata["schema_valid"] = bool(state.claim_id and state.member_id)
        return state

    async def _check_eligibility(self, state: RefundWorkflowState) -> RefundWorkflowState:
        result = await check_refund_eligibility(
            state.member_id, state.claim_id, state.amount_usd
        )
        state.metadata["eligible"] = result["eligible"]
        state.metadata.setdefault("tool_calls", []).append(
            {"tool": "check_refund_eligibility", "result": result}
        )
        state.steps.append("check_eligibility")
        if not result["eligible"]:
            state.metadata["refund_status"] = "denied"
        return state

    async def _request_consent(self, state: RefundWorkflowState) -> RefundWorkflowState:
        state.steps.append("request_consent")
        if not state.user_confirmed:
            state.metadata["refund_status"] = "pending_consent"
        return state

    async def _execute_refund(self, state: RefundWorkflowState) -> RefundWorkflowState:
        if not state.metadata.get("eligible") or not state.user_confirmed:
            return state

        result = await process_refund(
            member_id=state.member_id,
            claim_id=state.claim_id,
            amount_usd=state.amount_usd,
            user_confirmed=True,
            idempotency_key=f"{state.claim_id}-{state.amount_usd}",
        )
        state.metadata.setdefault("tool_calls", []).append(
            {"tool": "process_refund", "result": result}
        )
        state.metadata["refund_status"] = result["status"]
        if result.get("refund_id"):
            state.metadata["refund_id"] = result["refund_id"]
        state.steps.append("execute_refund")
        return state

    async def _track_finance(self, state: RefundWorkflowState) -> RefundWorkflowState:
        if state.metadata.get("refund_id"):
            tracked = await track_finance(state.metadata["refund_id"])
            state.metadata.setdefault("tool_calls", []).append(
                {"tool": "track_finance", "result": tracked}
            )
        state.steps.append("action_complete")
        return state
