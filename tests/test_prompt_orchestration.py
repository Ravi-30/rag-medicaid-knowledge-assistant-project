"""Tests for prompt-only orchestration → agents → MCP flow."""

import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestration import GraphOrchestrator
from healthcare_agents.orchestration.mcp_planner import plan_mcp_tools_for_agent
from healthcare_agents.orchestration.state import WorkflowState


def test_mcp_planner_eligibility():
    state = WorkflowState(query="check eligibility", member_id="member-001")
    tools = plan_mcp_tools_for_agent("eligibility", state)
    assert tools[0][0] == "get_profile"
    assert tools[0][1]["member_id"] == "member-001"


@pytest.mark.asyncio
async def test_prompt_only_routes_and_invokes_mcp():
    orchestrator = GraphOrchestrator()
    result = await orchestrator.run(
        "Check Medicaid eligibility for member-001",
        context=AgentContext(member_id="member-001", role="provider"),
    )
    assert result.agent_name == "eligibility_agent"
    assert "eligibility" in result.metadata.get("agents_invoked", [])
    assert result.metadata.get("orchestrated_by") == "graph_orchestrator"
    assert "get_profile" in result.metadata.get("mcp_tools_used", [])


@pytest.mark.asyncio
async def test_prompt_only_appointment_routing():
    orchestrator = GraphOrchestrator()
    result = await orchestrator.run(
        "Book a primary care appointment next week",
        context=AgentContext(member_id="member-001", role="member"),
    )
    assert "service_appointment" in result.metadata.get("agents_invoked", [])
    assert "check_availability" in result.metadata.get("mcp_tools_used", [])
