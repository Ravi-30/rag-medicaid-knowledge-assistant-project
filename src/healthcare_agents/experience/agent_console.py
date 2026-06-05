"""Agent console for support staff — Layer 1."""

from typing import Any

from healthcare_agents.control import HumanInTheLoop
from healthcare_agents.context import PersistentMemory
from healthcare_agents.experience.dashboard import DashboardAPI


class AgentConsole:
    """Support agent workspace — cases, handoffs, HITL actions."""

    def __init__(
        self,
        dashboard: DashboardAPI | None = None,
        hitl: HumanInTheLoop | None = None,
        memory: PersistentMemory | None = None,
    ):
        self.memory = memory or PersistentMemory()
        self.hitl = hitl or HumanInTheLoop()
        self.dashboard = dashboard or DashboardAPI(self.memory, self.hitl)

    def list_pending_handoffs(self) -> list[dict[str, Any]]:
        return self.dashboard.get_pending_handoffs()

    def acknowledge_handoff(self, escalation_id: str, agent_id: str) -> dict[str, Any]:
        return self.dashboard.acknowledge_handoff(escalation_id, agent_id)

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        return self.dashboard.get_case(case_id)
