"""Guided handoff workflow — seamless human escalation (LangGraph-style)."""

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from healthcare_agents.agents.base import AgentContext, AgentResult
from healthcare_agents.control.hitl import HumanInTheLoop
from healthcare_agents.orchestration.escalation_triggers import detect_escalation_triggers
from healthcare_agents.schemas.escalation import EscalationResolution, HandoffPackage
from healthcare_agents.safety.phi_guard import PHIGuard


@dataclass
class EscalationWorkflowState:
    query: str
    context: AgentContext
    escalation_id: str = ""
    triggers: list[str] = field(default_factory=list)
    handoff: HandoffPackage | None = None
    steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class EscalationHandoffWorkflow:
    """Escalation Agent — prepare context, HITL gateway, sync resolution."""

    name = "escalation_agent"

    def __init__(self, hitl: HumanInTheLoop | None = None, phi_guard: PHIGuard | None = None):
        self.hitl = hitl or HumanInTheLoop()
        self.phi_guard = phi_guard or PHIGuard()

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        state = EscalationWorkflowState(query=query, context=context)
        state.escalation_id = f"ESC-{uuid4().hex[:8].upper()}"

        confidence = float(context.metadata.get("confidence", 0.5))
        clarification_count = int(context.metadata.get("clarification_count", 0))
        state.triggers = detect_escalation_triggers(
            query, context.metadata, confidence, clarification_count
        )
        if not state.triggers:
            state.triggers = ["user_request"]

        state = await self._prepare_handoff(state)
        state = await self._submit_to_hitl_gateway(state)
        state = await self._await_ack(state)

        content = (
            f"Escalation — Human Handoff\n"
            f"Escalation ID: {state.escalation_id}\n"
            f"Priority: {state.handoff.priority if state.handoff else 'normal'}\n"
            f"Triggers: {', '.join(state.triggers)}\n"
            f"Status: {state.metadata.get('hitl_status', 'pending_ack')}\n\n"
            f"Context Summary:\n{state.handoff.context_summary if state.handoff else ''}\n\n"
            f"Recommended Next Steps:\n"
            + "\n".join(f"- {s}" for s in (state.handoff.recommended_next_steps if state.handoff else []))
        )

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.95,
            metadata={
                "escalation_id": state.escalation_id,
                "triggers": state.triggers,
                "handoff": state.handoff.model_dump() if state.handoff else {},
                "hitl_status": state.metadata.get("hitl_status"),
                "workflow_steps": state.steps,
                "requires_hitl": True,
            },
        )

    async def resolve(
        self,
        escalation_id: str,
        resolution_notes: str,
        actions_taken: list[str] | None = None,
        status: str = "resolved",
    ) -> EscalationResolution:
        """Sync human resolution back to the system (knowledge capture)."""
        resolution = EscalationResolution(
            escalation_id=escalation_id,
            status=status,
            resolution_notes=resolution_notes,
            actions_taken=actions_taken or [],
            knowledge_tags=["escalation_resolved", "human_handoff"],
        )
        self.hitl.record_resolution(escalation_id, resolution.model_dump())
        return resolution

    async def _prepare_handoff(self, state: EscalationWorkflowState) -> EscalationWorkflowState:
        ctx = state.context
        history = ctx.metadata.get("action_history", [])
        if isinstance(history, list):
            action_lines = [str(h) for h in history]
        else:
            action_lines = []

        trace = ctx.metadata.get("trace", [])
        if trace:
            action_lines.extend(f"{t.get('name', 'step')}" for t in trace if isinstance(t, dict))

        summary_parts = [
            f"Query: {self.phi_guard.sanitize(state.query[:300])}",
            f"Member: {ctx.member_id or 'unknown'}",
            f"Source agent: {ctx.metadata.get('source_agent', 'unknown')}",
        ]
        if ctx.rag_context:
            summary_parts.append(f"Policy context: {len(ctx.rag_context)} documents")

        priority = ctx.metadata.get("priority", "normal")
        if "risk_flag" in state.triggers or ctx.metadata.get("risk_level") == "high":
            priority = "urgent"
        elif "low_confidence" in state.triggers:
            priority = "high"

        recommended = _recommend_next_steps(state.triggers, ctx)

        state.handoff = HandoffPackage(
            escalation_id=state.escalation_id,
            case_id=ctx.case_id,
            member_id=ctx.member_id,
            source_agent=str(ctx.metadata.get("source_agent", "")),
            priority=priority,
            triggers=state.triggers,
            context_summary="\n".join(summary_parts),
            action_history=action_lines[:20],
            recommended_next_steps=recommended,
        )
        state.steps.append("prepare_handoff")
        return state

    async def _submit_to_hitl_gateway(self, state: EscalationWorkflowState) -> EscalationWorkflowState:
        assert state.handoff is not None
        case_id = state.handoff.case_id or state.escalation_id
        self.hitl.create_handoff(
            escalation_id=state.escalation_id,
            case_id=case_id,
            handoff_package=state.handoff.model_dump(),
            priority=state.handoff.priority,
        )
        state.metadata["hitl_status"] = "pending_ack"
        state.steps.append("submit_hitl_gateway")
        return state

    async def _await_ack(self, state: EscalationWorkflowState) -> EscalationWorkflowState:
        record = self.hitl.get_handoff(state.escalation_id)
        if record and record.get("status") == "acknowledged":
            state.metadata["hitl_status"] = "acknowledged"
        state.steps.append("await_ack")
        return state


def _recommend_next_steps(triggers: list[str], ctx: AgentContext) -> list[str]:
    steps: list[str] = []
    if "low_confidence" in triggers:
        steps.append("Review AI-generated response and verify against policy manual.")
    if "repeated_failure" in triggers:
        steps.append("Complete member verification and retry workflow manually.")
    if "policy_restriction" in triggers:
        steps.append("Apply policy exception approval if warranted.")
    if "user_request" in triggers:
        steps.append("Acknowledge member and address request directly.")
    if not steps:
        steps.append("Review case context and determine appropriate resolution.")
    return steps
