"""Business rules and coverage policy validation (Layer 6)."""

from dataclasses import dataclass
from typing import Any


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    rule_id: str | None = None


class PolicyEngine:
    """Evaluates agent actions against business rules before execution."""

    _RULES: list[dict[str, Any]] = [
        {
            "id": "PA-001",
            "action": "submit_prior_auth",
            "requires": ["member_id", "procedure_code", "clinical_notes"],
        },
        {
            "id": "CLM-001",
            "action": "submit_claim",
            "requires": ["member_id", "provider_npi", "service_date"],
        },
        {
            "id": "ELG-001",
            "action": "verify_eligibility",
            "requires": ["member_id"],
        },
        {
            "id": "REF-001",
            "action": "process_refund",
            "requires": ["member_id", "claim_id", "amount_usd"],
        },
        {
            "id": "INQ-001",
            "action": "submit_inquiry",
            "requires": [],
        },
    ]

    def evaluate(self, action: str, payload: dict[str, Any]) -> PolicyDecision:
        rule = next((r for r in self._RULES if r["action"] == action), None)
        if not rule:
            return PolicyDecision(allowed=True, reason="No policy rule defined for action.")

        missing = [field for field in rule["requires"] if not payload.get(field)]
        if missing:
            return PolicyDecision(
                allowed=False,
                reason=f"Missing required fields: {', '.join(missing)}",
                rule_id=rule["id"],
            )
        return PolicyDecision(
            allowed=True,
            reason="Policy requirements satisfied.",
            rule_id=rule["id"],
        )
