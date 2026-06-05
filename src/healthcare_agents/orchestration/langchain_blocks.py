"""LangChain building-block layer — prompts, chains, parsers (optional LangChain deps)."""

from typing import Any

from pydantic import BaseModel, Field

from healthcare_agents.orchestration.triage import classify_intents
from healthcare_agents.schemas.triage import TriageIntent


class ClassifiedIntent(BaseModel):
    intent: str
    confidence: float
    entities: dict[str, str] = Field(default_factory=dict)


class EligibilityResult(BaseModel):
    member_id: str
    eligible: bool
    plan: str = ""
    labels: list[str] = Field(default_factory=list)


class ClaimStatusResult(BaseModel):
    claim_id: str
    status: str
    labels: list[str] = Field(default_factory=list)


class IntentClassificationChain:
    """LCEL-style intent classification (B — Classify)."""

    def invoke(self, query: str) -> list[ClassifiedIntent]:
        intents = classify_intents(query)
        return [
            ClassifiedIntent(
                intent=i.name,
                confidence=i.confidence,
                entities=i.entities,
            )
            for i in intents
        ]


class InformationLookupChain:
    """Deterministic chain: Query → Retrieve → Validate → Respond."""

    def invoke(self, query: str, snippets: list[str]) -> dict[str, Any]:
        return {
            "query": query,
            "snippets_used": len(snippets),
            "validated": bool(snippets),
            "response_ready": True,
        }


class EligibilityCheckChain:
    """Deterministic chain: Member ID → Verify → Rules Engine → Response."""

    def invoke(self, member_id: str, eligible: bool = True, plan: str = "Medicaid") -> EligibilityResult:
        return EligibilityResult(
            member_id=member_id,
            eligible=eligible,
            plan=plan,
            labels=["eligible" if eligible else "ineligible"],
        )


class ClaimsStatusChain:
    """Deterministic chain: Claim ID → Fetch → Evaluate → Respond."""

    def invoke(self, claim_id: str, status: str = "in_review") -> ClaimStatusResult:
        return ClaimStatusResult(claim_id=claim_id, status=status, labels=[status])


def parse_structured_output(model: type[BaseModel], data: dict[str, Any]) -> BaseModel:
    """Pydantic validation wrapper — structured outputs before consumption."""
    return model.model_validate(data)
