"""Human-in-the-loop gateway — handoff packages, ACK, resolution sync."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class HITLCheckpoint:
    case_id: str
    step: str
    reason: str
    payload: dict[str, Any]
    status: str = "pending"


@dataclass
class HandoffRecord:
    escalation_id: str
    case_id: str
    handoff_package: dict[str, Any]
    priority: str = "normal"
    status: str = "pending_ack"
    resolution: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class HumanInTheLoop:
    """HITL gateway for checkpoints, escalations, and human resolution sync."""

    _HIGH_RISK_ACTIONS = frozenset(
        {
            "deny_prior_auth",
            "approve_high_cost_claim",
            "terminate_coverage",
            "release_phi",
            "process_refund",
        }
    )

    def __init__(self) -> None:
        self._checkpoints: dict[str, HITLCheckpoint] = {}
        self._handoffs: dict[str, HandoffRecord] = {}

    def requires_review(self, action: str, metadata: dict[str, Any] | None = None) -> bool:
        if action in self._HIGH_RISK_ACTIONS:
            return True
        meta = metadata or {}
        return meta.get("cost_usd", 0) > 10_000 or meta.get("risk_level") == "high"

    def create_checkpoint(
        self,
        case_id: str,
        step: str,
        reason: str,
        payload: dict[str, Any],
    ) -> HITLCheckpoint:
        checkpoint = HITLCheckpoint(
            case_id=case_id,
            step=step,
            reason=reason,
            payload=payload,
        )
        self._checkpoints[case_id] = checkpoint
        return checkpoint

    def get_checkpoint(self, case_id: str) -> HITLCheckpoint | None:
        return self._checkpoints.get(case_id)

    def approve(self, case_id: str) -> HITLCheckpoint | None:
        checkpoint = self._checkpoints.get(case_id)
        if checkpoint:
            checkpoint.status = "approved"
        return checkpoint

    def create_handoff(
        self,
        escalation_id: str,
        case_id: str,
        handoff_package: dict[str, Any],
        priority: str = "normal",
    ) -> HandoffRecord:
        record = HandoffRecord(
            escalation_id=escalation_id,
            case_id=case_id,
            handoff_package=handoff_package,
            priority=priority,
        )
        self._handoffs[escalation_id] = record
        return record

    def get_handoff(self, escalation_id: str) -> dict[str, Any] | None:
        record = self._handoffs.get(escalation_id)
        if not record:
            return None
        return {
            "escalation_id": record.escalation_id,
            "case_id": record.case_id,
            "priority": record.priority,
            "status": record.status,
            "handoff_package": record.handoff_package,
            "resolution": record.resolution,
        }

    def acknowledge(self, escalation_id: str, agent_id: str = "human_agent") -> HandoffRecord | None:
        record = self._handoffs.get(escalation_id)
        if record:
            record.status = "acknowledged"
            record.handoff_package["assigned_to"] = agent_id
        return record

    def record_resolution(self, escalation_id: str, resolution: dict[str, Any]) -> None:
        record = self._handoffs.get(escalation_id)
        if record:
            record.resolution = resolution
            record.status = resolution.get("status", "resolved")

    def list_pending_handoffs(self) -> list[dict[str, Any]]:
        return [
            {
                "escalation_id": r.escalation_id,
                "case_id": r.case_id,
                "priority": r.priority,
                "status": r.status,
            }
            for r in self._handoffs.values()
            if r.status in ("pending_ack", "acknowledged", "in_progress")
        ]
