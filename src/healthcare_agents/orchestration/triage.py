"""Triage & Routing — classification, ReAct routing, multi-intent, escalation."""

from healthcare_agents.orchestration.routing import ROUTING_RULES, route_query
from healthcare_agents.schemas.triage import TriageIntent, TriageResult

_VAGUE_PATTERNS = ("help with my", "i need help", "assist me", "not sure")
_URGENT_PATTERNS = ("urgent", "emergency", "immediately", "asap", "critical")
_HIGH_PATTERNS = ("refund", "denied", "fraud", "complaint", "escalat")

_INTENT_AGENT_MAP: list[tuple[list[str], str]] = [
    (["schedule", "appointment", "book", "referral", "availability"], "service_appointment"),
    (["order", "fulfillment", "shipment", "delivery", "track order"], "order_management"),
    (["refund", "billing", "payment", "charge"], "billing_refund"),
    *ROUTING_RULES,
]


def classify_intents(query: str) -> list[TriageIntent]:
    """LCEL-style classification — detect one or more intents in the query."""
    lower = query.lower()
    intents: list[TriageIntent] = []

    for keywords, agent in _INTENT_AGENT_MAP:
        matched = [kw for kw in keywords if kw in lower]
        if matched:
            confidence = min(0.95, 0.55 + len(matched) * 0.12)
            intents.append(
                TriageIntent(
                    name=agent,
                    confidence=confidence,
                    entities={"matched_keywords": ", ".join(matched)},
                )
            )

    if not intents:
        intents.append(TriageIntent(name="knowledge", confidence=0.45))

    intents.sort(key=lambda i: i.confidence, reverse=True)
    return _dedupe_intents(intents)


def _dedupe_intents(intents: list[TriageIntent]) -> list[TriageIntent]:
    seen: set[str] = set()
    unique: list[TriageIntent] = []
    for intent in intents:
        if intent.name not in seen:
            seen.add(intent.name)
            unique.append(intent)
    return unique


def score_priority(query: str, intents: list[TriageIntent]) -> str:
    lower = query.lower()
    if any(p in lower for p in _URGENT_PATTERNS):
        return "urgent"
    if any(p in lower for p in _HIGH_PATTERNS):
        return "high"
    if len(intents) > 1:
        return "high"
    return "normal"


def react_select_agent(
    query: str,
    intents: list[TriageIntent],
    member_id: str | None,
    clarification_count: int = 0,
) -> TriageResult:
    """Lightweight ReAct routing — resolve ambiguity and missing entities."""
    lower = query.lower()
    primary = intents[0].name if intents else "knowledge"
    targets = [i.name for i in intents[:3]]
    confidence = intents[0].confidence if intents else 0.4
    priority = score_priority(query, intents)

    missing_member = primary in {
        "eligibility",
        "authorization",
        "claims",
        "service_appointment",
        "billing_refund",
        "order_management",
    } and not member_id

    missing_procedure = primary == "authorization" and "procedure" not in lower

    if any(p in lower for p in _VAGUE_PATTERNS) and len(lower.split()) < 8:
        if clarification_count >= 1:
            return TriageResult(
                primary_agent="escalation",
                target_agents=["escalation"],
                priority="normal",
                intents=intents,
                confidence=0.5,
                escalate=True,
                explanation="Repeated vague input — escalating to human agent.",
            )
        return TriageResult(
            primary_agent=primary,
            target_agents=targets,
            priority=priority,
            intents=intents,
            confidence=confidence,
            needs_clarification=True,
            clarification_prompt=(
                "Could you share more details? For example: member ID, type of request "
                "(eligibility, claim, prior auth, appointment, or billing)."
            ),
            explanation="Query too broad for confident routing.",
        )

    if missing_member:
        return TriageResult(
            primary_agent=primary,
            target_agents=targets,
            priority=priority,
            intents=intents,
            confidence=confidence,
            needs_clarification=True,
            clarification_prompt="Please provide your member ID to continue.",
            explanation=f"Routing to {primary} but member ID is required.",
        )

    if missing_procedure:
        return TriageResult(
            primary_agent=primary,
            target_agents=targets,
            priority=priority,
            intents=intents,
            confidence=confidence,
            needs_clarification=True,
            clarification_prompt="Which procedure or service requires prior authorization?",
            explanation="Prior auth routing requires procedure details.",
        )

    if len(intents) > 1 and confidence >= 0.5:
        return TriageResult(
            primary_agent=primary,
            target_agents=targets,
            priority=priority,
            intents=intents,
            confidence=confidence,
            explanation=f"Multi-intent query — primary: {primary}, also: {targets[1:]}",
        )

    return TriageResult(
        primary_agent=primary,
        target_agents=targets or [primary],
        priority=priority,
        intents=intents,
        confidence=confidence,
        explanation=f"Clear intent routed to {primary}.",
    )


def triage_request(
    query: str,
    member_id: str | None = None,
    clarification_count: int = 0,
) -> TriageResult:
    """Full triage pipeline: classify → priority → ReAct route."""
    intents = classify_intents(query)
    if len(intents) == 1 and intents[0].name == "knowledge":
        fallback = route_query(query)
        if fallback != "knowledge":
            intents = [TriageIntent(name=fallback, confidence=0.7)]
    return react_select_agent(query, intents, member_id, clarification_count)
