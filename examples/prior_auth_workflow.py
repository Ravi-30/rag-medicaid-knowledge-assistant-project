"""Demo: end-to-end prior authorization workflow for XYZ Healthcare Corp."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestration import GraphOrchestrator


async def main() -> None:
    orchestrator = GraphOrchestrator(use_llm=False)

    context = AgentContext(
        member_id="member-001",
        role="provider",
        clinical_notes="Patient presents with chronic knee pain. MRI recommended for surgical planning.",
        metadata={
            "procedure_code": "MRI",
            "provider_npi": "1234567890",
        },
    )

    print("=" * 60)
    print("PRIOR AUTHORIZATION WORKFLOW")
    print("=" * 60)

    steps = ["eligibility", "authorization", "policy_compliance"]
    results = await orchestrator.run_workflow(
        query="Submit prior authorization for MRI and verify member eligibility",
        steps=steps,
        context=context,
    )

    for i, result in enumerate(results, 1):
        print(f"\n--- Step {i}: {result.agent_name} ---")
        print(result.content)
        if result.metadata:
            print(f"Metadata: {result.metadata}")


if __name__ == "__main__":
    asyncio.run(main())
