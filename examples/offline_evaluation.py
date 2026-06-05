"""Offline evaluation stack demo."""

import asyncio
import json

from healthcare_agents import GraphOrchestrator
from healthcare_agents.agents.base import AgentContext
from healthcare_agents.evaluation import AgentEvalCase, OfflineEvaluationStack


async def main():
    orchestrator = GraphOrchestrator()
    stack = OfflineEvaluationStack()

    result = await orchestrator.run(
        "Check Medicaid eligibility for member-001",
        agent="eligibility",
        context=AgentContext(member_id="member-001", role="provider"),
    )

    offline = stack.evaluate_case(
        prediction=result.content,
        reference="Member member-001 is eligible for Medicaid coverage.",
        retrieved=["policy-eligibility-001", "policy-medicaid-002", "policy-general-003"],
        relevant={"policy-eligibility-001", "policy-medicaid-002"},
        k=3,
        agent_result={
            "agent_name": result.agent_name,
            "content": result.content,
            "confidence": result.confidence,
            "tool_calls": result.tool_calls,
            "metadata": result.metadata,
        },
        steps_completed=result.metadata.get("workflow_metrics", {}).get("steps", []),
        metadata=result.metadata,
        expected_agent="eligibility",
        evaluation_events=result.metadata.get("evaluation", []),
        deepeval_case=AgentEvalCase(
            input="Check Medicaid eligibility for member-001",
            expected_output="Member is eligible for Medicaid coverage.",
            expected_agent="eligibility",
        ),
    )

    print("Offline Evaluation Report")
    print("=" * 40)
    print(json.dumps(offline.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
