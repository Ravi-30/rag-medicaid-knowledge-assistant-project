"""Workflow state for LangGraph orchestration (Layer 2)."""

from dataclasses import dataclass, field
from typing import Any, Literal

OperationalAgentType = Literal[
    "eligibility",
    "authorization",
    "claims",
    "provider",
    "care_mgmt",
    "policy_compliance",
    "triage_routing",
    "knowledge",
    "member_support",
    "fraud",
    "escalation",
    "memory_context",
    "service_appointment",
    "billing_refund",
    "order_management",
    "auto",
]


@dataclass
class WorkflowState:
    """Stateful graph state passed between orchestration nodes."""

    query: str
    member_id: str | None = None
    case_id: str | None = None
    session_id: str | None = None
    role: str = "ops_analyst"
    selected_agent: str = ""
    agent_result: dict[str, Any] | None = None
    rag_context: list[str] = field(default_factory=list)
    engineered_context: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)
    reflection: dict[str, Any] = field(default_factory=dict)
    triage_result: dict[str, Any] = field(default_factory=dict)
    tool_outputs: dict[str, Any] = field(default_factory=dict)
    artifact: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    needs_clarification: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    requires_hitl: bool = False
    escalate: bool = False
    blocked: bool = False
    status: str = "running"
    steps_completed: list[str] = field(default_factory=list)

    def to_context_metadata(self) -> dict[str, Any]:
        return {**self.metadata, "case_id": self.case_id, "session_id": self.session_id}
