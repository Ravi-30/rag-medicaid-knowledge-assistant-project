"""Plan MCP tool invocations for orchestrated domain agents."""

from typing import Any

from healthcare_agents.orchestration.state import WorkflowState

# Legacy/direct tool names → MCP registry names
TOOL_ALIASES: dict[str, str] = {
    "verify_eligibility": "get_profile",
    "lookup_provider": "verify_network",
    "check_availability": "check_availability",
    "book_appointment": "book_appointment",
    "get_claim_status": "get_case_status",
}

# Domain agent → MCP tools the orchestrator should invoke
AGENT_MCP_TOOLS: dict[str, list[str]] = {
    "eligibility": ["get_profile"],
    "authorization": ["verify_identity"],
    "claims": ["get_case_status"],
    "provider": ["verify_network"],
    "service_appointment": ["check_availability"],
    "billing_refund": ["check_refund_eligibility"],
    "order_management": ["track_order"],
    "member_support": ["get_profile"],
    "fraud": ["get_case_status"],
}


def resolve_tool_name(name: str) -> str:
    return TOOL_ALIASES.get(name, name)


def build_tool_payload(tool_name: str, state: WorkflowState) -> dict[str, Any]:
    """Build MCP payload from workflow state."""
    member_id = state.member_id or state.metadata.get("member_id") or "member-unknown"
    meta = state.metadata

    if tool_name in ("get_profile", "verify_identity", "check_refund_eligibility"):
        return {"member_id": member_id}
    if tool_name == "get_case_status":
        return {"claim_id": meta.get("claim_id", "CLM-UNKNOWN")}
    if tool_name == "check_availability":
        return {
            "member_id": member_id,
            "service_type": meta.get("service_type", "primary_care"),
        }
    if tool_name == "book_appointment":
        return {
            "member_id": member_id,
            "slot": meta.get("selected_slot", "2026-06-10T09:00:00"),
            "service_type": meta.get("service_type", "primary_care"),
        }
    if tool_name == "track_order":
        return {"order_id": meta.get("order_id", "ORD-UNKNOWN")}
    if tool_name == "verify_network":
        return {"npi": meta.get("provider_npi", "1234567890")}
    return {"member_id": member_id}


def plan_mcp_tools_for_agent(agent: str, state: WorkflowState) -> list[tuple[str, dict[str, Any]]]:
    """Return MCP tools the orchestrator should call for a domain agent."""
    planned: list[tuple[str, dict[str, Any]]] = []
    for tool_name in AGENT_MCP_TOOLS.get(agent, []):
        planned.append((tool_name, build_tool_payload(tool_name, state)))
    return planned


def plan_mcp_tools_for_chain(agents: list[str], state: WorkflowState) -> list[tuple[str, dict[str, Any]]]:
    """Plan MCP tools for all agents in the orchestration chain."""
    seen: set[str] = set()
    planned: list[tuple[str, dict[str, Any]]] = []
    for agent in agents:
        for tool_name, payload in plan_mcp_tools_for_agent(agent, state):
            if tool_name not in seen:
                seen.add(tool_name)
                planned.append((tool_name, payload))
    return planned


def tool_calls_from_agent(agent_tool_calls: list[dict[str, Any]], state: WorkflowState) -> list[tuple[str, dict[str, Any]]]:
    """Normalize agent-emitted tool calls to MCP invocations."""
    planned: list[tuple[str, dict[str, Any]]] = []
    for call in agent_tool_calls:
        raw_name = call.get("tool") or call.get("name", "")
        if not raw_name:
            continue
        name = resolve_tool_name(raw_name)
        payload = call.get("payload") or call.get("arguments") or build_tool_payload(name, state)
        planned.append((name, payload))
    return planned
