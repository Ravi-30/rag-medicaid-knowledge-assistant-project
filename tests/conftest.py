"""Shared pytest fixtures."""

import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestration import GraphOrchestrator


@pytest.fixture
def member_context() -> AgentContext:
    return AgentContext(member_id="member-001", role="provider")


@pytest.fixture
def orchestrator() -> GraphOrchestrator:
    return GraphOrchestrator()
