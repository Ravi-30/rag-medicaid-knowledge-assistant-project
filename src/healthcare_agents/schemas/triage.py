"""Structured triage output — classification, routing, and explainability."""

from pydantic import BaseModel, Field


class TriageIntent(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    entities: dict[str, str] = Field(default_factory=dict)


class TriageResult(BaseModel):
    """Explainable structured output from the Triage & Routing Agent."""

    primary_agent: str
    target_agents: list[str] = Field(default_factory=list)
    priority: str = "normal"  # low | normal | high | urgent
    intents: list[TriageIntent] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    needs_clarification: bool = False
    clarification_prompt: str | None = None
    escalate: bool = False
    explanation: str = ""
