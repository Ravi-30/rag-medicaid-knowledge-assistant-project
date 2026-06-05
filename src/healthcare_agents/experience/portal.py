"""Self-service portal stub — Layer 1."""

from typing import Any

from healthcare_agents.use_cases import (
    AppointmentBookingUseCase,
    ClaimsRefundUseCase,
    ClaimsTroubleshootingUseCase,
)


class SelfServicePortal:
    """Member and provider portal actions."""

    def __init__(self):
        self.appointment = AppointmentBookingUseCase()
        self.refund = ClaimsRefundUseCase()
        self.troubleshooting = ClaimsTroubleshootingUseCase()

    async def book_appointment(self, member_id: str, query: str, **metadata: Any):
        from healthcare_agents.agents.base import AgentContext

        ctx = AgentContext(member_id=member_id, role="member", metadata=metadata)
        return await self.appointment.execute(query, context=ctx)

    async def request_refund(self, member_id: str, query: str, **metadata: Any):
        from healthcare_agents.agents.base import AgentContext

        ctx = AgentContext(member_id=member_id, role="member", metadata=metadata)
        return await self.refund.execute(query, context=ctx)

    async def troubleshoot(self, member_id: str, query: str, **metadata: Any):
        from healthcare_agents.agents.base import AgentContext

        ctx = AgentContext(member_id=member_id, role="member", metadata=metadata)
        return await self.troubleshooting.execute(query, context=ctx)
