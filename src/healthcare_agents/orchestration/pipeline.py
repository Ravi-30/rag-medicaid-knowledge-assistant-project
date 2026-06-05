"""LangGraph orchestration pipeline — maps design nodes A–K to implementation."""

from enum import StrEnum


class OrchestrationNode(StrEnum):
    """XYZ Healthcare Corp LangGraph orchestration nodes."""

    GUARD_INPUT = "guard_input"  # Input validation
    TRIAGE = "triage"  # A — Classify & Prioritize
    CONTEXT_ENRICHMENT = "context_enrichment"  # Parallel lookup + RAG
    SELECT_AGENT = "select_agent"  # B — Route to domain agent
    PLANNING = "planning"  # E — Domain agent plan
    GOVERNED_DECISION = "governed_decision"  # Policy engine gate
    TOOL_EXECUTION = "tool_execution"  # G — MCP servers
    EXECUTE_AGENT = "execute_agent"  # Domain agent action
    REFLECTION = "reflection"  # H — ReAct loop: did step succeed?
    ESCALATION_GATE = "escalation_gate"  # I — HITL gating
    ESCALATION = "escalation"  # J — Audit & handoff
    RESPONSE = "response"  # Structured response generation
    PERSIST = "persist"  # Bookmarks, checkpoints, resume
    ACTION_COMPLETE = "action_complete"  # K — Deterministic artifact


# Design diagram → code module reference
NODE_MAP: dict[OrchestrationNode, str] = {
    OrchestrationNode.TRIAGE: "orchestration/triage.py",
    OrchestrationNode.CONTEXT_ENRICHMENT: "context/pipeline.py",
    OrchestrationNode.PLANNING: "orchestration/graph.py::_node_reasoning",
    OrchestrationNode.GOVERNED_DECISION: "control/policy_engine.py",
    OrchestrationNode.TOOL_EXECUTION: "tools/mcp/governance.py",
    OrchestrationNode.REFLECTION: "orchestration/graph.py::_node_reflect",
    OrchestrationNode.ESCALATION: "workflows/escalation_handoff.py",
    OrchestrationNode.PERSIST: "context/memory.py",
}

SEQUENTIAL_PIPELINE: list[OrchestrationNode] = [
    OrchestrationNode.GUARD_INPUT,
    OrchestrationNode.TRIAGE,
    OrchestrationNode.CONTEXT_ENRICHMENT,
    OrchestrationNode.SELECT_AGENT,
    OrchestrationNode.PLANNING,
    OrchestrationNode.EXECUTE_AGENT,
    OrchestrationNode.GOVERNED_DECISION,
    OrchestrationNode.TOOL_EXECUTION,
    OrchestrationNode.REFLECTION,
    OrchestrationNode.ESCALATION_GATE,
    OrchestrationNode.RESPONSE,
    OrchestrationNode.PERSIST,
    OrchestrationNode.ACTION_COMPLETE,
]
