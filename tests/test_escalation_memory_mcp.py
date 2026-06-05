"""Tests for Escalation, Memory & Context, and MCP server design."""

import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.control import HumanInTheLoop
from healthcare_agents.orchestration import GraphOrchestrator
from healthcare_agents.orchestration.escalation_triggers import detect_escalation_triggers
from healthcare_agents.tools.mcp import list_servers
from healthcare_agents.workflows import ActiveMemoryWorkflow, EscalationHandoffWorkflow


def test_mcp_server_categories():
    servers = list_servers()
    assert "customer_identity" in servers
    assert "service_scheduling" in servers
    assert "billing_refunds" in servers
    assert "order_management" in servers
    assert "diagnostics" in servers
    assert "notifications" in servers


def test_escalation_triggers_low_confidence():
    triggers = detect_escalation_triggers("help me", confidence=0.3)
    assert "low_confidence" in triggers


def test_escalation_triggers_user_request():
    triggers = detect_escalation_triggers("I want to speak to a human agent")
    assert "user_request" in triggers


@pytest.mark.asyncio
async def test_escalation_handoff_workflow():
    hitl = HumanInTheLoop()
    workflow = EscalationHandoffWorkflow(hitl=hitl)
    ctx = AgentContext(
        member_id="member-001",
        case_id="case-abc",
        metadata={
            "source_agent": "claims_agent",
            "confidence": 0.3,
            "action_history": ["verify_eligibility", "submit_claim"],
        },
    )
    result = await workflow.run(ctx, "Claim keeps failing, need a supervisor")
    assert result.metadata.get("escalation_id")
    assert result.metadata.get("handoff")
    assert "prepare_handoff" in result.metadata["workflow_steps"]


@pytest.mark.asyncio
async def test_escalation_resolve_syncs_back():
    hitl = HumanInTheLoop()
    workflow = EscalationHandoffWorkflow(hitl=hitl)
    ctx = AgentContext(member_id="member-001", metadata={"confidence": 0.2})
    result = await workflow.run(ctx, "Escalate this case")
    esc_id = result.metadata["escalation_id"]
    resolution = await workflow.resolve(esc_id, "Issue resolved manually", ["approved_claim"])
    assert resolution.status == "resolved"
    handoff = hitl.get_handoff(esc_id)
    assert handoff["resolution"]["status"] == "resolved"


@pytest.mark.asyncio
async def test_active_memory_workflow():
    workflow = ActiveMemoryWorkflow()
    ctx = AgentContext(
        member_id="member-001",
        session_id="sess-001",
        case_id="case-001",
        rag_context=["policy.pdf: eligibility rules"],
        metadata={"eligible": False},
    )
    result = await workflow.run(ctx, "Check my coverage status")
    artifact = result.metadata["artifact"]
    assert "summarize_and_store" in result.metadata["workflow_steps"]
    assert artifact["summarized_context"]


@pytest.mark.asyncio
async def test_graph_escalation_agent():
    orchestrator = GraphOrchestrator()
    ctx = AgentContext(
        member_id="member-001",
        metadata={"confidence": 0.2, "clarification_count": 2},
    )
    result = await orchestrator.run("I need a human agent please", agent="escalation", context=ctx)
    assert result.agent_name == "escalation_agent"
    assert result.metadata.get("escalation_id")
