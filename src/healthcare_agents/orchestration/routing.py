"""Agent routing — triage and route requests to domain agents."""

from typing import Any

ROUTING_RULES: list[tuple[list[str], str]] = [
    (["schedule", "appointment", "book", "availability", "referral visit"], "service_appointment"),
    (["order", "fulfillment", "shipment", "track order", "dme"], "order_management"),
    (["refund", "billing dispute", "payment issue"], "billing_refund"),
    (["eligibility", "eligible", "benefits", "coverage"], "eligibility"),
    (["prior auth", "authorization", "pre-auth", "pa request"], "authorization"),
    (["fraud", "duplicate", "suspicious", "integrity"], "fraud"),
    (["claim", "adjudication", "billing", "refund"], "claims"),
    (["provider", "referral", "network", "npi", "credential"], "provider"),
    (["care plan", "care management", "outreach"], "care_mgmt"),
    (["escalat", "supervisor", "handoff", "complaint"], "escalation"),
    (["policy", "compliance", "hipaa", "regulation"], "policy_compliance"),
    (["help", "support", "my account", "member portal"], "member_support"),
    (["how to", "what is", "explain", "troubleshoot", "guide"], "knowledge"),
    (["context", "history", "remember", "previous"], "memory_context"),
]


def route_query(query: str, metadata: dict[str, Any] | None = None) -> str:
    """Select the best domain agent for a query."""
    meta = metadata or {}
    if meta.get("force_agent"):
        return meta["force_agent"]

    lower = query.lower()
    for keywords, agent in ROUTING_RULES:
        if any(kw in lower for kw in keywords):
            return agent
    return "knowledge"


def route_with_confidence(query: str) -> dict[str, Any]:
    """Return routing decision with confidence score."""
    agent = route_query(query)
    lower = query.lower()
    matches = sum(1 for kws, a in ROUTING_RULES if a == agent for kw in kws if kw in lower)
    confidence = min(0.95, 0.5 + matches * 0.15)
    return {"agent": agent, "confidence": confidence, "query": query}
