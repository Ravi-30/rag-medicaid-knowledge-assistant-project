"""Resolve which domain agents the orchestrator should invoke after triage."""

from healthcare_agents.orchestration.routing import route_query
from healthcare_agents.schemas.triage import TriageResult

# Meta-agents used for routing/context — not primary handlers for member requests
_META_AGENTS = frozenset({"triage_routing", "memory_context"})


def resolve_agent_chain(triage: TriageResult, query: str = "") -> list[str]:
    """Build ordered agent execution chain from triage output."""
    if triage.escalate:
        return ["escalation"]

    chain: list[str] = []

    def add(agent: str | None) -> None:
        if not agent or agent in _META_AGENTS or agent in chain:
            return
        chain.append(agent)

    add(triage.primary_agent)
    for agent in triage.target_agents:
        add(agent)

    if not chain and query:
        add(route_query(query))

    if not chain:
        add("knowledge")

    return chain[:4]


def primary_agent(chain: list[str]) -> str:
    return chain[0] if chain else "knowledge"
