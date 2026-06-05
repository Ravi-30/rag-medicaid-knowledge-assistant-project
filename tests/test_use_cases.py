"""Tests for XYZ Healthcare Corp end-to-end use cases."""

import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.use_cases import (
    AppointmentBookingUseCase,
    ClaimsRefundUseCase,
    ClaimsTroubleshootingUseCase,
)


@pytest.mark.asyncio
async def test_uc1_appointment_booking_pending_or_complete():
    uc = AppointmentBookingUseCase()
    ctx = AgentContext(member_id="member-001", role="member")
    result = await uc.execute("Book appointment for back pain next week", context=ctx)
    assert result.use_case == "uc1_appointment_booking"
    assert result.status in ("pending_confirmation", "completed", "needs_info")
    assert any(s.name == "triage_routing" for s in result.steps)


@pytest.mark.asyncio
async def test_uc1_appointment_confirmed():
    uc = AppointmentBookingUseCase()
    ctx = AgentContext(
        member_id="member-001",
        role="member",
        metadata={"user_confirmed": True, "service_type": "primary_care"},
    )
    result = await uc.execute("Schedule primary care appointment", context=ctx)
    assert result.status == "completed"
    assert result.metadata.get("appointment_id")


@pytest.mark.asyncio
async def test_uc2_claims_refund_complete():
    uc = ClaimsRefundUseCase()
    ctx = AgentContext(
        member_id="member-001",
        metadata={
            "claim_id": "CLM-REF001",
            "amount_usd": 250.0,
            "user_confirmed": True,
        },
    )
    result = await uc.execute(
        "I was charged $250 for a lab test. I want a refund.",
        context=ctx,
    )
    assert result.use_case == "uc2_claims_refund"
    assert result.status in ("completed", "pending_confirmation")
    assert any(s.name == "billing_agent_validation" for s in result.steps)


@pytest.mark.asyncio
async def test_uc2_refund_hitl_for_high_amount():
    uc = ClaimsRefundUseCase()
    ctx = AgentContext(
        member_id="member-001",
        metadata={"claim_id": "CLM-HIGH", "amount_usd": 5000.0},
    )
    result = await uc.execute("Refund overcharge of $5000", context=ctx)
    assert result.status == "pending_confirmation"
    assert any(s.name == "hitl_gating" for s in result.steps)


@pytest.mark.asyncio
async def test_uc3_troubleshooting_denied_claim():
    uc = ClaimsTroubleshootingUseCase()
    ctx = AgentContext(
        member_id="member-001",
        metadata={"claim_id": "CLM-DENIED-001"},
    )
    result = await uc.execute(
        "My claim was denied and I don't understand why.",
        context=ctx,
    )
    assert result.use_case == "uc3_claims_troubleshooting"
    assert result.status in ("completed", "escalated", "needs_info")
    assert result.metadata.get("root_cause")
    assert any(s.name == "context_retrieval" for s in result.steps)
