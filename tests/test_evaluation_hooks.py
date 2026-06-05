"""Tests for runtime evaluation hooks."""

import pytest

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.evaluation import EvaluationEventType, RuntimeEvaluationHooks
from healthcare_agents.orchestration import GraphOrchestrator


def test_runtime_hooks_log_all_event_types():
    captured: list[str] = []
    hooks = RuntimeEvaluationHooks(
        audit_callback=lambda event, data: captured.append(event),
    )
    hooks.begin_run(case_id="case-1", member_id="member-001", query="test query")

    hooks.log_evidence_retrieved(
        snippets=["policy: rule 1"],
        sources=["policy.pdf"],
        token_estimate=42,
    )
    hooks.log_tools_chosen(tools=["get_profile"], agent="eligibility")
    hooks.log_policy_outcome(action="verify_eligibility", allowed=True, reason="ok")
    hooks.log_execution_result(agent="eligibility", success=True, confidence=0.9, summary="Eligible")
    hooks.log_reflection_decision(confidence=0.9, escalate=False, resolved=True)
    hooks.log_escalation_event(escalation_id="ESC-1", reason="Low confidence")

    events = hooks.get_events()
    types = {e["event_type"] for e in events}
    assert EvaluationEventType.EVIDENCE_RETRIEVED in types
    assert EvaluationEventType.TOOLS_CHOSEN in types
    assert EvaluationEventType.POLICY_OUTCOME in types
    assert EvaluationEventType.EXECUTION_RESULT in types
    assert EvaluationEventType.REFLECTION_DECISION in types
    assert EvaluationEventType.ESCALATION_EVENT in types

    summary = hooks.get_summary()
    assert summary["total_events"] >= 7
    assert summary["run_id"] is not None


def test_event_callback_fires():
    received = []
    hooks = RuntimeEvaluationHooks(event_callback=lambda e: received.append(e.event_type))
    hooks.begin_run(query="hello")
    hooks.log_policy_outcome(action="submit_claim", allowed=False, reason="missing fields")
    assert received[-1] == EvaluationEventType.POLICY_OUTCOME


@pytest.mark.asyncio
async def test_orchestrator_attaches_evaluation_log():
    orchestrator = GraphOrchestrator()
    result = await orchestrator.run(
        "Check Medicaid eligibility",
        agent="eligibility",
        context=AgentContext(member_id="member-001", role="provider"),
    )
    assert "evaluation" in result.metadata
    assert "evaluation_summary" in result.metadata
    events = result.metadata["evaluation"]
    event_types = {e["event_type"] for e in events}
    assert EvaluationEventType.EVIDENCE_RETRIEVED in event_types
    assert EvaluationEventType.POLICY_OUTCOME in event_types
    assert EvaluationEventType.EXECUTION_RESULT in event_types
    assert EvaluationEventType.REFLECTION_DECISION in event_types


@pytest.mark.asyncio
async def test_orchestrator_logs_escalation_event():
    orchestrator = GraphOrchestrator()
    result = await orchestrator.run(
        "I need a human agent please",
        agent="escalation",
        context=AgentContext(member_id="member-001", metadata={"confidence": 0.2}),
    )
    event_types = {e["event_type"] for e in result.metadata.get("evaluation", [])}
    assert EvaluationEventType.ESCALATION_EVENT in event_types or EvaluationEventType.REFLECTION_DECISION in event_types
