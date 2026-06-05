"""Tests for seven-layer system design modules."""

import pytest

from healthcare_agents.agents.registry import DOMAIN_AGENTS, list_domain_agents
from healthcare_agents.api.app import HealthcareAPIService
from healthcare_agents.api.auth import AuthService
from healthcare_agents.data import DataLayer
from healthcare_agents.experience.agent_console import AgentConsole
from healthcare_agents.experience.portal import SelfServicePortal
from healthcare_agents.experience.voice import VoiceInterface


def test_domain_agent_registry():
    agents = list_domain_agents()
    assert len(agents) == len(DOMAIN_AGENTS)
    names = {a["name"] for a in agents}
    assert "appointment_agent" in names
    assert "care_coordination_agent" in names


def test_auth_service_demo_keys():
    auth = AuthService()
    ctx = auth.authenticate("member-demo-key")
    assert ctx is not None
    assert ctx.role == "member"
    assert auth.authorize(ctx, "read")


@pytest.mark.asyncio
async def test_api_service_health_and_agent_run():
    service = HealthcareAPIService()
    assert service.health()["status"] == "ok"
    result = await service.run_agent(
        "Check my eligibility",
        member_id="member-001",
        role="member",
    )
    assert "content" in result
    assert "agent" in result


@pytest.mark.asyncio
async def test_api_service_use_case():
    service = HealthcareAPIService()
    result = await service.run_use_case(
        "appointment_booking",
        "Book a primary care visit next week",
        member_id="member-001",
    )
    assert result["use_case"] == "uc1_appointment_booking"
    assert len(result["steps"]) >= 1


@pytest.mark.asyncio
async def test_data_layer():
    layer = DataLayer()
    member = await layer.get_member_context("member-001")
    assert member["member_id"] == "member-001"


@pytest.mark.asyncio
async def test_experience_stubs():
    voice = VoiceInterface()
    session = voice.create_session(member_id="member-001")
    result = await voice.handle_transcript(session, "Hello")
    assert result.content

    portal = SelfServicePortal()
    uc = await portal.book_appointment("member-001", "Book visit")
    assert uc.use_case == "uc1_appointment_booking"

    console = AgentConsole()
    assert isinstance(console.list_pending_handoffs(), list)
