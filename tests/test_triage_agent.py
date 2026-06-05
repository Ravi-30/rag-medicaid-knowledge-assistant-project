import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.agents.triage_agent import TriageAgent


@pytest.mark.asyncio
async def test_triage_mild_symptoms():
    agent = TriageAgent()
    context = AgentContext(symptoms=["headache"])
    result = await agent.run(context, "I have a mild headache")

    assert result.agent_name == "triage_agent"
    assert result.metadata["care_level"] == "self-care"
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_triage_red_flag():
    agent = TriageAgent()
    context = AgentContext(symptoms=["chest pain", "shortness of breath"])
    result = await agent.run(context, "Chest pain and difficulty breathing")

    assert result.metadata["care_level"] == "emergency"
    assert result.metadata["urgency_score"] >= 9


@pytest.mark.asyncio
async def test_triage_fever():
    agent = TriageAgent()
    context = AgentContext(symptoms=["fever"])
    result = await agent.run(context, "I have a fever")

    assert result.metadata["care_level"] == "primary_care"
