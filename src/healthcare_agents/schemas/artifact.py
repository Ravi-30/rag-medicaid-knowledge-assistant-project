"""Deterministic result artifacts — structured outputs from completed workflows."""

from typing import Any

from pydantic import BaseModel, Field


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str = ""
    labels: list[str] = Field(default_factory=list)


class ResultArtifact(BaseModel):
    """Policy-driven, deterministic output ready for downstream systems."""

    artifact_type: str  # refund_completed | claim_updated | appointment_booked | ...
    status: str  # completed | pending_confirmation | escalated | denied
    member_id: str | None = None
    case_id: str | None = None
    summary: str = ""
    policy_decision: PolicyDecision | None = None
    tool_outputs: dict[str, Any] = Field(default_factory=dict)
    audit_ref: str | None = None
