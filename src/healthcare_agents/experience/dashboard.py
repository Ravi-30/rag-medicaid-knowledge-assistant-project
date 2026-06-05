"""Support dashboard API stub for agent handoff and case management (Layer 1).

Full React dashboard is out of scope for this package; this module exposes
case and checkpoint data for integration with a frontend application.
"""

from typing import Any

from healthcare_agents.context import PersistentMemory
from healthcare_agents.control import HumanInTheLoop


class DashboardAPI:
    """Read-only API surface for support dashboard integrations."""

    def __init__(
        self,
        memory: PersistentMemory | None = None,
        hitl: HumanInTheLoop | None = None,
    ):
        self.memory = memory or PersistentMemory()
        self.hitl = hitl or HumanInTheLoop()

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        record = self.memory.get_case(case_id)
        if not record:
            return None
        return {
            "case_id": record.case_id,
            "member_id": record.member_id,
            "status": record.status,
            "workflow_type": record.workflow_type,
            "history": [{"role": e.role, "content": e.content} for e in record.history],
            "metadata": record.metadata,
        }

    def get_pending_checkpoints(self) -> list[dict[str, Any]]:
        return [
            {
                "case_id": cp.case_id,
                "step": cp.step,
                "reason": cp.reason,
                "status": cp.status,
            }
            for cp in self.hitl._checkpoints.values()
            if cp.status == "pending"
        ]

    def get_pending_handoffs(self) -> list[dict[str, Any]]:
        return self.hitl.list_pending_handoffs()

    def get_handoff(self, escalation_id: str) -> dict[str, Any] | None:
        return self.hitl.get_handoff(escalation_id)

    def acknowledge_handoff(self, escalation_id: str, agent_id: str = "human_agent") -> dict[str, Any]:
        record = self.hitl.acknowledge(escalation_id, agent_id)
        if not record:
            return {"error": "not_found"}
        return {"escalation_id": escalation_id, "status": record.status}

    def approve_checkpoint(self, case_id: str) -> dict[str, Any] | None:
        checkpoint = self.hitl.approve(case_id)
        if not checkpoint:
            return None
        return {"case_id": case_id, "status": checkpoint.status}
