import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.agents.platform import (
    FraudAgent,
    KnowledgeTroubleshootingAgent,
    TriageRoutingAgent,
)
from healthcare_agents.context.pipeline import ContextEngineeringPipeline
from healthcare_agents.orchestration.routing import route_query
from healthcare_agents.tools.mcp import MCPToolRegistry


@pytest.mark.asyncio
async def test_route_query_eligibility():
    assert route_query("Check Medicaid eligibility") == "eligibility"


@pytest.mark.asyncio
async def test_route_query_fraud():
    assert route_query("Investigate suspicious duplicate claim") == "fraud"


def test_context_pipeline_select_compress():
    pipeline = ContextEngineeringPipeline(max_snippets=2, max_chars=500)
    result = pipeline.run(
        rag_results=["doc1: " + "x" * 300, "doc2: short", "doc3: unused"],
        query="eligibility check",
    )
    assert len(result.snippets) <= 2
    assert result.token_estimate > 0


@pytest.mark.asyncio
async def test_mcp_tool_invoke():
    registry = MCPToolRegistry()
    result = await registry.invoke("get_profile", {"member_id": "member-001"})
    assert result.success
    assert result.data["eligible"] is True


@pytest.mark.asyncio
async def test_triage_routing_agent():
    agent = TriageRoutingAgent()
    result = await agent.run(AgentContext(), "Verify member eligibility")
    assert "routed_agent" in result.metadata
    assert result.metadata["routed_agent"] == "eligibility"


@pytest.mark.asyncio
async def test_knowledge_agent_uses_rag():
    agent = KnowledgeTroubleshootingAgent()
    ctx = AgentContext(rag_context=["policy.pdf: Prior auth required for MRI"])
    result = await agent.run(ctx, "What is the prior auth policy for MRI?")
    assert "policy.pdf" in result.content


@pytest.mark.asyncio
async def test_fraud_agent_flags_risk():
    agent = FraudAgent()
    result = await agent.run(
        AgentContext(metadata={"claim_id": "CLM-123"}),
        "Suspicious duplicate fraud claim",
    )
    assert result.metadata["risk_level"] in ("medium", "high")
