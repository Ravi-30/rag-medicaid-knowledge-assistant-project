from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """Shared context passed between agents in a workflow."""

    patient_id: str | None = None
    member_id: str | None = None
    case_id: str | None = None
    session_id: str | None = None
    role: str = "ops_analyst"
    symptoms: list[str] = field(default_factory=list)
    clinical_notes: str = ""
    rag_context: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def subject_id(self) -> str | None:
        """Member or patient identifier used for enterprise lookups."""
        return self.member_id or self.patient_id


@dataclass
class AgentResult:
    """Standardized output from any agent."""

    agent_name: str
    content: str
    confidence: float = 0.0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all healthcare agents."""

    name: str = "base_agent"
    description: str = ""

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    @abstractmethod
    async def run(self, context: AgentContext, query: str) -> AgentResult:
        """Execute the agent's task given context and a user query."""

    def _build_system_prompt(self, context: AgentContext | None = None) -> str:
        base = (
            f"You are {self.name}, a healthcare AI assistant. "
            f"{self.description} "
            "Always prioritize patient safety. Never provide definitive diagnoses. "
            "Recommend consulting a licensed healthcare provider for medical decisions."
        )
        if context and context.metadata.get("prompt_guidance"):
            return f"{base}\n\nGuardrails: {context.metadata['prompt_guidance']}"
        return base
