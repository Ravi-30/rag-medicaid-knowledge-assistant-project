"""DeepEval integration for end-to-end and agent evaluation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentEvalCase:
    input: str
    expected_output: str
    context: list[str] = field(default_factory=list)
    expected_agent: str | None = None
    retrieval_context: list[str] = field(default_factory=list)


@dataclass
class DeepEvalResult:
    case_input: str
    actual_output: str
    passed: bool
    score: float
    metric: str
    backend: str
    details: dict[str, Any] = field(default_factory=dict)


def _fallback_relevancy(actual: str, expected: str) -> DeepEvalResult:
    actual_tokens = set(actual.lower().split())
    expected_tokens = set(expected.lower().split())
    overlap = len(actual_tokens & expected_tokens) / max(len(expected_tokens), 1)
    return DeepEvalResult(
        case_input="",
        actual_output=actual,
        passed=overlap >= 0.3,
        score=overlap,
        metric="answer_relevancy_fallback",
        backend="fallback",
    )


def evaluate_case_with_deepeval(case: AgentEvalCase, actual_output: str) -> DeepEvalResult:
    """Run DeepEval answer relevancy when deepeval is installed."""
    try:
        from deepeval.metrics import AnswerRelevancyMetric
        from deepeval.test_case import LLMTestCase

        test_case = LLMTestCase(
            input=case.input,
            actual_output=actual_output,
            expected_output=case.expected_output,
            retrieval_context=case.retrieval_context or case.context,
        )
        metric = AnswerRelevancyMetric(threshold=0.5)
        score = metric.measure(test_case)
        passed = metric.is_successful()
        return DeepEvalResult(
            case_input=case.input,
            actual_output=actual_output,
            passed=passed,
            score=float(score),
            metric="answer_relevancy",
            backend="deepeval",
            details={"threshold": 0.5},
        )
    except ImportError:
        result = _fallback_relevancy(actual_output, case.expected_output)
        result.case_input = case.input
        return result
    except Exception as exc:
        result = _fallback_relevancy(actual_output, case.expected_output)
        result.case_input = case.input
        result.details = {"error": str(exc), "backend": "deepeval_error_fallback"}
        return result


def run_deepeval_suite(cases: list[tuple[AgentEvalCase, str]]) -> list[DeepEvalResult]:
    """Evaluate a batch of agent outputs with DeepEval."""
    return [evaluate_case_with_deepeval(case, actual) for case, actual in cases]
