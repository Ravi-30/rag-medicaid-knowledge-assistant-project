"""Tests for offline evaluation stack."""

import pytest

from healthcare_agents.evaluation import (
    AgentEvalCase,
    OfflineEvaluationStack,
    evaluate_branching,
    evaluate_retrieval,
    precision_at_k,
    recall_at_k,
)
from healthcare_agents.evaluation.generation_metrics import evaluate_generation
from healthcare_agents.evaluation.safety_metrics import evaluate_safety
from healthcare_agents.evaluation.workflow_metrics import evaluate_workflow


def test_precision_and_recall_at_k():
    retrieved = ["doc-a", "doc-b", "doc-c", "doc-d"]
    relevant = {"doc-a", "doc-c", "doc-x"}

    assert precision_at_k(retrieved, relevant, k=2) == 0.5
    assert recall_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)
    metrics = evaluate_retrieval(retrieved, relevant, k=4)
    assert metrics.hits == 2
    assert metrics.precision_at_k == 0.5


def test_generation_metrics_fallback():
    metrics = evaluate_generation(
        "Member is eligible for Medicaid coverage.",
        "Member member-001 is eligible for Medicaid.",
    )
    assert metrics.rouge_1 > 0
    assert metrics.bertscore_f1 > 0
    assert metrics.backend in ("fallback", "rouge-score", "rouge-score+bert-score")


def test_safety_metrics_fallback_clean_text():
    metrics = evaluate_safety("Your eligibility has been verified successfully.")
    assert not metrics.flagged
    assert metrics.backend in ("fallback", "detoxify")


def test_safety_metrics_fallback_toxic_text():
    metrics = evaluate_safety("You are stupid and worthless.")
    assert metrics.flagged
    assert metrics.toxicity > 0


def test_workflow_branching_correct():
    steps = ["triage", "context_engineering", "execute:eligibility", "reflect"]
    assert evaluate_branching(steps, "eligibility")


def test_workflow_branching_incorrect():
    steps = ["triage", "execute:claims", "reflect"]
    assert not evaluate_branching(steps, "eligibility")


def test_workflow_metrics_success_and_branching():
    metrics = evaluate_workflow(
        agent_result={"content": "Eligible", "tool_calls": [], "confidence": 0.9},
        steps_completed=["execute:eligibility"],
        metadata={"blocked": False},
        expected_agent="eligibility",
    )
    assert metrics.successful_completion
    assert metrics.correct_branching
    assert metrics.actual_agent == "eligibility"


def test_deepeval_fallback():
    stack = OfflineEvaluationStack()
    result = stack.evaluate_deepeval(
        AgentEvalCase(
            input="Check eligibility",
            expected_output="Member is eligible for coverage.",
        ),
        "Member is eligible for Medicaid coverage.",
    )
    assert result.backend in ("fallback", "deepeval", "deepeval_error_fallback")
    assert 0.0 <= result.score <= 1.0


def test_offline_stack_full_case():
    stack = OfflineEvaluationStack()
    report = stack.evaluate_case(
        prediction="Member member-001 is eligible for Medicaid coverage.",
        reference="Member member-001 is eligible for Medicaid.",
        retrieved=["doc-a", "doc-b", "doc-c"],
        relevant={"doc-a", "doc-b"},
        k=2,
        agent_result={"content": "Eligible", "tool_calls": [], "confidence": 0.95},
        steps_completed=["execute:eligibility"],
        metadata={"blocked": False},
        expected_agent="eligibility",
        deepeval_case=AgentEvalCase(
            input="Check eligibility",
            expected_output="Member is eligible.",
        ),
    )
    data = report.to_dict()
    assert data["retrieval"] is not None
    assert data["generation"] is not None
    assert data["safety"] is not None
    assert data["workflow"] is not None
    assert data["deepeval"] is not None
    assert "passed" in data["summary"]
