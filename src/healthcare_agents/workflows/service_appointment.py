"""Hybrid LangGraph workflow: identify → availability → confirm → book → complete."""

from dataclasses import dataclass, field
from typing import Any

from healthcare_agents.agents.base import AgentContext, AgentResult
from healthcare_agents.tools.scheduling import book_appointment, check_availability


@dataclass
class AppointmentWorkflowState:
    query: str
    member_id: str
    service_type: str = "primary_care"
    provider_npi: str | None = None
    selected_slot: str | None = None
    user_confirmed: bool = False
    steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ServiceAppointmentWorkflow:
    """Service & Appointment Agent — conversational + agentic hybrid scheduling."""

    name = "service_appointment_agent"

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        member_id = context.subject_id or context.metadata.get("member_id", "")
        if not member_id:
            return AgentResult(
                agent_name=self.name,
                content="Member ID required to schedule a service appointment.",
                confidence=0.0,
                metadata={"needs_clarification": True},
            )

        state = AppointmentWorkflowState(
            query=query,
            member_id=member_id,
            service_type=context.metadata.get("service_type", _infer_service(query)),
            provider_npi=context.metadata.get("provider_npi"),
            user_confirmed=context.metadata.get("user_confirmed", False),
            selected_slot=context.metadata.get("selected_slot"),
        )

        state = await self._identify_service_need(state)
        state = await self._fetch_availability(state)
        state = await self._confirm_with_user(state)
        state = await self._execute_booking(state)

        content = (
            f"Service & Appointment\n"
            f"Service: {state.service_type}\n"
            f"Status: {state.metadata.get('booking_status', 'pending')}\n"
            f"Steps: {' → '.join(state.steps)}"
        )
        if state.metadata.get("appointment_id"):
            content += f"\nAppointment ID: {state.metadata['appointment_id']}"
        if state.metadata.get("available_slots") and not state.user_confirmed:
            slots = state.metadata["available_slots"]
            content += f"\nAvailable slots: {', '.join(slots)}"
            content += "\nPlease confirm your preferred slot to complete booking."

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.9 if state.metadata.get("appointment_id") else 0.7,
            tool_calls=state.metadata.get("tool_calls", []),
            metadata={
                **state.metadata,
                "workflow_steps": state.steps,
                "needs_confirmation": not state.user_confirmed
                and bool(state.metadata.get("available_slots")),
            },
        )

    async def _identify_service_need(self, state: AppointmentWorkflowState) -> AppointmentWorkflowState:
        state.steps.append("identify_service_need")
        state.metadata["intent"] = "schedule_appointment"
        return state

    async def _fetch_availability(self, state: AppointmentWorkflowState) -> AppointmentWorkflowState:
        if state.metadata.get("available_slots"):
            state.steps.append("fetch_availability_cached")
            return state

        result = await check_availability(
            state.member_id, state.service_type, state.provider_npi
        )
        state.metadata["available_slots"] = result["available_slots"]
        state.metadata.setdefault("tool_calls", []).append(
            {"tool": "check_availability", "result": result}
        )
        if not state.selected_slot and result["available_slots"]:
            state.selected_slot = result["available_slots"][0]
        state.steps.append("fetch_availability")
        return state

    async def _confirm_with_user(self, state: AppointmentWorkflowState) -> AppointmentWorkflowState:
        state.steps.append("confirm_with_user")
        if not state.user_confirmed:
            state.metadata["booking_status"] = "awaiting_confirmation"
        return state

    async def _execute_booking(self, state: AppointmentWorkflowState) -> AppointmentWorkflowState:
        if not state.selected_slot:
            return state

        result = await book_appointment(
            member_id=state.member_id,
            slot=state.selected_slot,
            service_type=state.service_type,
            provider_npi=state.provider_npi,
            confirmed=state.user_confirmed,
        )
        state.metadata.setdefault("tool_calls", []).append(
            {"tool": "book_appointment", "result": result}
        )
        state.metadata["booking_status"] = result["status"]
        if result.get("appointment_id"):
            state.metadata["appointment_id"] = result["appointment_id"]
        state.steps.append("execute_booking")
        state.steps.append("action_complete")
        return state


def _infer_service(query: str) -> str:
    lower = query.lower()
    if "specialist" in lower or "referral" in lower:
        return "specialist_referral"
    if "mri" in lower or "imaging" in lower:
        return "diagnostic_imaging"
    return "primary_care"
