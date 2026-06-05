"""Tests for LangGraph orchestration design alignment."""

import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestration import GraphOrchestrator
from healthcare_agents.orchestration.langchain_blocks import (
    ClaimsStatusChain,
    EligibilityCheckChain,
    IntentClassificationChain,
)
from healthcare_agents.orchestration.pipeline import OrchestrationNode, SEQUENTIAL_PIPELINE
from healthcare_agents.orchestration.triage import triage_request
from healthcare_agents.tools.mcp.governance import MCPGovernanceLayer
from healthcare_agents.tools.mcp.registry import MCPToolRegistry


def test_orchestration_pipeline_nodes():
    assert OrchestrationNode.TRIAGE in SEQUENTIAL_PIPELINE
    assert OrchestrationNode.REFLECTION in SEQUENTIAL_PIPELINE
    assert OrchestrationNode.ACTION_COMPLETE == SEQUENTIAL_PIPELINE[-1]


def test_triage_classifies_eligibility():
    result = triage_request("Verify Medicaid eligibility", member_id="member-001")
    assert result.primary_agent == "eligibility"
    assert result.confidence > 0.4


def test_langchain_blocks_chains():
    intents = IntentClassificationChain().invoke("Book an appointment next week")
    assert any(i.intent == "service_appointment" for i in intents)

    elig = EligibilityCheckChain().invoke("member-001")
    assert elig.eligible
    assert "eligible" in elig.labels

    claim = ClaimsStatusChain().invoke("CLM-001")
    assert claim.status == "in_review"


@pytest.mark.asyncio
async def test_orchestrator_produces_artifact():
    orchestrator = GraphOrchestrator()
    result = await orchestrator.run(
        "Check Medicaid eligibility",
        context=AgentContext(member_id="member-001", role="provider"),
    )
    assert result.agent_name == "eligibility_agent"
    assert "artifact" in result.metadata or result.content


@pytest.mark.asyncio
async def test_orchestrator_triage_clarification():
    orchestrator = GraphOrchestrator()
    result = await orchestrator.run("help with my account")
    assert result.agent_name in ("triage_agent", "graph_orchestrator", "knowledge_agent")


@pytest.mark.asyncio
async def test_mcp_governance_blocks_circuit():
    registry = MCPToolRegistry()
    governance = MCPGovernanceLayer(failure_threshold=1, cooldown_seconds=60)
    tool = registry.get("get_profile")
    assert tool is not None

    async def failing_handler(**kwargs):
        raise RuntimeError("simulated failure")

    tool.handler = failing_handler
    result = await governance.invoke(tool, {"member_id": "member-001"})
    assert not result.success

    circuit = await governance.invoke(tool, {"member_id": "member-001"})
    assert not circuit.success
    assert "Circuit open" in (circuit.error or "")
