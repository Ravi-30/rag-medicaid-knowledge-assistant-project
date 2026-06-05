"""Offline evaluation stack — DeepEval, ROUGE, BERTScore, Detoxify, retrieval, workflow."""

from dataclasses import dataclass, field
from typing import Any

from healthcare_agents.evaluation.deepeval_runner import AgentEvalCase, DeepEvalResult, evaluate_case_with_deepeval
from healthcare_agents.evaluation.generation_metrics import GenerationMetrics, evaluate_generation
from healthcare_agents.evaluation.retrieval_metrics import RetrievalMetrics, evaluate_retrieval
from healthcare_agents.evaluation.safety_metrics import SafetyMetrics, evaluate_safety
from healthcare_agents.evaluation.workflow_metrics import WorkflowEvalMetrics, evaluate_workflow


@dataclass
class OfflineEvalResult:
    retrieval: RetrievalMetrics | None = None
    generation: GenerationMetrics | None = None
    safety: SafetyMetrics | None = None
    workflow: WorkflowEvalMetrics | None = None
    deepeval: DeepEvalResult | None = None
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval": _maybe_dict(self.retrieval),
            "generation": _maybe_dict(self.generation),
            "safety": _maybe_dict(self.safety),
            "workflow": _maybe_dict(self.workflow),
            "deepeval": _maybe_dict(self.deepeval),
            "summary": self.summary,
        }


def _maybe_dict(obj: Any) -> dict[str, Any] | None:
    if obj is None:
        return None
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(obj)
    return dict(obj)


class OfflineEvaluationStack:
    """Unified offline evaluation for agentic healthcare workflows."""

    def evaluate_retrieval(
        self,
        retrieved: list[str],
        relevant: set[str],
        k: int = 5,
    ) -> RetrievalMetrics:
        return evaluate_retrieval(retrieved, relevant, k=k)

    def evaluate_generation(self, prediction: str, reference: str) -> GenerationMetrics:
        return evaluate_generation(prediction, reference)

    def evaluate_safety(self, text: str) -> SafetyMetrics:
        return evaluate_safety(text)

    def evaluate_workflow(
        self,
        *,
        agent_result: dict[str, Any] | None,
        steps_completed: list[str],
        metadata: dict[str, Any],
        expected_agent: str | None = None,
        evaluation_events: list[dict[str, Any]] | None = None,
    ) -> WorkflowEvalMetrics:
        return evaluate_workflow(
            agent_result=agent_result,
            steps_completed=steps_completed,
            metadata=metadata,
            expected_agent=expected_agent,
            evaluation_events=evaluation_events,
        )

    def evaluate_deepeval(self, case: AgentEvalCase, actual_output: str) -> DeepEvalResult:
        return evaluate_case_with_deepeval(case, actual_output)

    def evaluate_case(
        self,
        *,
        prediction: str,
        reference: str,
        retrieved: list[str] | None = None,
        relevant: set[str] | None = None,
        k: int = 5,
        agent_result: dict[str, Any] | None = None,
        steps_completed: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        expected_agent: str | None = None,
        evaluation_events: list[dict[str, Any]] | None = None,
        deepeval_case: AgentEvalCase | None = None,
    ) -> OfflineEvalResult:
        """Run the full offline evaluation stack for a single test case."""
        result = OfflineEvalResult()

        if retrieved is not None and relevant is not None:
            result.retrieval = self.evaluate_retrieval(retrieved, relevant, k=k)

        result.generation = self.evaluate_generation(prediction, reference)
        result.safety = self.evaluate_safety(prediction)

        if steps_completed is not None and metadata is not None:
            result.workflow = self.evaluate_workflow(
                agent_result=agent_result,
                steps_completed=steps_completed,
                metadata=metadata,
                expected_agent=expected_agent,
                evaluation_events=evaluation_events,
            )

        if deepeval_case is not None:
            result.deepeval = self.evaluate_deepeval(deepeval_case, prediction)

        result.summary = self._build_summary(result)
        return result

    def _build_summary(self, result: OfflineEvalResult) -> dict[str, Any]:
        passed = True
        reasons: list[str] = []

        if result.retrieval and result.retrieval.recall_at_k < 0.5:
            passed = False
            reasons.append("low_retrieval_recall")

        if result.generation and result.generation.rouge_l < 0.2:
            passed = False
            reasons.append("low_generation_quality")

        if result.safety and result.safety.flagged:
            passed = False
            reasons.append("safety_flag")

        if result.workflow and not result.workflow.successful_completion:
            passed = False
            reasons.append("workflow_incomplete")

        if result.workflow and not result.workflow.correct_branching:
            passed = False
            reasons.append("incorrect_branching")

        if result.deepeval and not result.deepeval.passed:
            passed = False
            reasons.append("deepeval_failed")

        return {
            "passed": passed,
            "reasons": reasons,
            "backends": {
                "generation": result.generation.backend if result.generation else None,
                "safety": result.safety.backend if result.safety else None,
                "deepeval": result.deepeval.backend if result.deepeval else None,
            },
        }
