"""Structured escalation handoff package."""

from pydantic import BaseModel, Field


class HandoffPackage(BaseModel):
    escalation_id: str
    case_id: str | None = None
    member_id: str | None = None
    source_agent: str = ""
    priority: str = "normal"
    triggers: list[str] = Field(default_factory=list)
    context_summary: str = ""
    action_history: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    status: str = "pending_ack"


class EscalationResolution(BaseModel):
    escalation_id: str
    status: str  # in_progress | resolved | rejected
    resolution_notes: str = ""
    actions_taken: list[str] = Field(default_factory=list)
    knowledge_tags: list[str] = Field(default_factory=list)
