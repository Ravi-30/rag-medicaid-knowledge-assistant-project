"""Escalation trigger detection — when to hand off to humans."""

from typing import Any

ESCALATION_TRIGGERS = (
    "low_confidence",
    "repeated_failure",
    "policy_restriction",
    "user_request",
    "risk_flag",
)


def detect_escalation_triggers(
    query: str,
    metadata: dict[str, Any] | None = None,
    confidence: float = 1.0,
    clarification_count: int = 0,
) -> list[str]:
    """Return active escalation trigger reasons."""
    meta = metadata or {}
    triggers: list[str] = []
    lower = query.lower()

    if confidence < 0.5:
        triggers.append("low_confidence")
    if clarification_count >= 2:
        triggers.append("repeated_failure")
    if meta.get("policy_blocked") or meta.get("requires_hitl"):
        triggers.append("policy_restriction")
    if any(kw in lower for kw in ("human agent", "supervisor", "speak to someone", "representative")):
        triggers.append("user_request")
    if meta.get("risk_level") == "high" or meta.get("escalate"):
        triggers.append("risk_flag")

    return triggers


def should_escalate(
    query: str,
    metadata: dict[str, Any] | None = None,
    confidence: float = 1.0,
    clarification_count: int = 0,
) -> bool:
    return bool(detect_escalation_triggers(query, metadata, confidence, clarification_count))
