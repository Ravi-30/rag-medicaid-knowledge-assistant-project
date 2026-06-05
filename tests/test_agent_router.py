"""Tests for orchestrator agent routing and multi-agent chains."""

import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestration import GraphOrchestrator
from healthcare_agents.orchestration.agent_router import resolve_agent_chain
from healthcare_agents.orchestration.triage import triage_request


def test_resolve_chain_eligibility():
    triage = triage_request("Check Medicaid eligibility", member_id="member-001")
    chain = resolve_agent_chain(triage, "Check Medicaid eligibility")
    assert chain[0] == "eligibility"
    assert "triage_routing" not in chain


def test_resolve_chain_appointment():
    triage = triage_request("Book an appointment next week", member_id="member-001")
    chain = resolve_agent_chain(triage)
    assert "service_appointment" in chain
    assert "policy_compliance" not in chain


@pytest.mark.asyncio
async def test_orchestrator_auto_routes_to_eligibility():
    orchestrator = GraphOrchestrator()
    result = await orchestrator.run(
        "Check Medicaid eligibility for this member",
        agent="auto",
        context=AgentContext(member_id="member-001", role="provider"),
    )
    assert result.agent_name == "eligibility_agent"
    assert "eligibility" in result.metadata.get("agents_invoked", [])


@pytest.mark.asyncio
async def test_orchestrator_auto_routes_appointment():
    orchestrator = GraphOrchestrator()
    result = await orchestrator.run(
        "Book a primary care appointment next week",
        agent="auto",
        context=AgentContext(member_id="member-001", role="member"),
    )
    invoked = result.metadata.get("agents_invoked", [])
    assert "service_appointment" in invoked
