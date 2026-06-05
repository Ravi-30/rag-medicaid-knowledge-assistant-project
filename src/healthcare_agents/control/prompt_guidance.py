"""Prompt-level guardrail guidance injected into agent system prompts."""

from dataclasses import dataclass

_BASE_GUIDANCE = (
    "You are a healthcare operations assistant. Never provide definitive medical diagnoses. "
    "Do not recommend stopping or changing prescribed medications. "
    "Route emergency symptoms to immediate care. "
    "Only invoke tools when required; never fabricate member, claim, or policy data. "
    "All actions must comply with HIPAA and organizational policy."
)

_ROLE_GUIDANCE: dict[str, str] = {
    "member": "You are assisting a health plan member. Verify identity before sharing PHI.",
    "provider": "You are assisting a credentialed provider. Confirm NPI when submitting claims or auth.",
    "ops_analyst": "You are assisting internal operations staff. Apply least-privilege data access.",
}

_ACTION_GUIDANCE: dict[str, str] = {
    "eligibility": "Confirm member_id before eligibility verification.",
    "authorization": "Prior auth requires procedure_code and clinical justification.",
    "claims": "Claim actions require member_id, provider_npi, and service_date.",
    "billing_refund": "Refunds above policy thresholds require human approval.",
    "process_refund": "Never process refunds without eligibility and fraud checks.",
    "fraud": "Flag suspicious activity; do not disclose investigation details to members.",
}


@dataclass
class PromptGuidanceResult:
    guidance: str
    layers_applied: list[str]


class PromptGuidance:
    """Layer 1 — prompt-level constraints for LLM reasoning."""

    def build(self, *, role: str = "ops_analyst", agent: str = "", query: str = "") -> PromptGuidanceResult:
        parts = [_BASE_GUIDANCE]
        layers = ["base"]

        if role in _ROLE_GUIDANCE:
            parts.append(_ROLE_GUIDANCE[role])
            layers.append("role")

        if agent in _ACTION_GUIDANCE:
            parts.append(_ACTION_GUIDANCE[agent])
            layers.append("action")

        lower = query.lower()
        if any(kw in lower for kw in ("refund", "billing", "payment")):
            parts.append(_ACTION_GUIDANCE["process_refund"])
            layers.append("context")

        return PromptGuidanceResult(guidance=" ".join(parts), layers_applied=layers)
