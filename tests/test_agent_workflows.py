"""Tests for agent-specific workflows from XYZ Healthcare Corp design."""

import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestration import GraphOrchestrator
from healthcare_agents.orchestration.triage import triage_request
from healthcare_agents.workflows import (
    BillingRefundWorkflow,
    OrderManagementWorkflow,
    ServiceAppointmentWorkflow,
)


@pytest.mark.asyncio
async def test_triage_clear_intent():
    result = triage_request(
        "Schedule a primary care appointment for member-001",
        member_id="member-001",
    )
    assert result.primary_agent == "service_appointment"
    assert not result.needs_clarification


@pytest.mark.asyncio
async def test_triage_ambiguous_escalates_on_repeat():
    result = triage_request("I need help with my account", clarification_count=1)
    assert result.escalate or result.needs_clarification


@pytest.mark.asyncio
async def test_triage_multi_intent():
    result = triage_request(
        "My claim was denied and I want a refund for the billing charge",
        member_id="member-001",
    )
    assert len(result.target_agents) >= 1
    assert result.priority in ("normal", "high", "urgent")


@pytest.mark.asyncio
async def test_service_appointment_workflow():
    workflow = ServiceAppointmentWorkflow()
    ctx = AgentContext(member_id="member-001", metadata={"user_confirmed": True})
    result = await workflow.run(ctx, "Book a primary care appointment")
    assert "fetch_availability" in result.metadata["workflow_steps"]
    assert result.metadata.get("appointment_id") or result.metadata.get("needs_confirmation")


@pytest.mark.asyncio
async def test_billing_refund_requires_consent():
    workflow = BillingRefundWorkflow()
    ctx = AgentContext(
        member_id="member-001",
        metadata={"claim_id": "CLM-123", "amount_usd": 150.0, "user_confirmed": False},
    )
    result = await workflow.run(ctx, "Process refund for denied claim")
    assert result.metadata.get("refund_status") == "pending_consent"


@pytest.mark.asyncio
async def test_billing_refund_executes_with_consent():
    workflow = BillingRefundWorkflow()
    ctx = AgentContext(
        member_id="member-001",
        role="ops_analyst",
        metadata={"claim_id": "CLM-123", "amount_usd": 150.0, "user_confirmed": True},
    )
    result = await workflow.run(ctx, "Process refund")
    assert result.metadata.get("refund_id")


@pytest.mark.asyncio
async def test_order_management_lifecycle():
    workflow = OrderManagementWorkflow()
    ctx = AgentContext(member_id="member-001", metadata={"items": ["wheelchair"]})
    result = await workflow.run(ctx, "Create DME fulfillment order")
    assert result.metadata.get("order_status")
    assert "complete" in result.metadata["workflow_steps"]


@pytest.mark.asyncio
async def test_graph_routes_appointment():
    orchestrator = GraphOrchestrator()
    ctx = AgentContext(member_id="member-001", role="member")
    result = await orchestrator.run("Schedule an appointment with my PCP", context=ctx)
    assert result.agent_name == "service_appointment_agent"
