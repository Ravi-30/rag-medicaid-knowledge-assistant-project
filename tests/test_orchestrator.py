import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_auto_selects_triage():
    orchestrator = Orchestrator()
    result = await orchestrator.run("I have a fever and cough")
    assert result.agent_name == "triage_agent"


@pytest.mark.asyncio
async def test_auto_selects_research():
    orchestrator = Orchestrator()
    result = await orchestrator.run("What are the drug interactions for warfarin?")
    assert result.agent_name == "research_agent"


@pytest.mark.asyncio
async def test_disclaimer_appended():
    orchestrator = Orchestrator()
    result = await orchestrator.run("headache", agent="triage")
    assert "Clinical Disclaimer" in result.content


@pytest.mark.asyncio
async def test_workflow_multiple_steps():
    orchestrator = Orchestrator()
    context = AgentContext(
        symptoms=["fever"],
        clinical_notes="Patient presents with fever. Assessment: viral URI.",
    )
    results = await orchestrator.run_workflow(
        "intake",
        steps=["triage", "clinical_summary"],
        context=context,
    )
    assert len(results) == 2
    assert results[0].agent_name == "triage_agent"
    assert results[1].agent_name == "clinical_summary_agent"
