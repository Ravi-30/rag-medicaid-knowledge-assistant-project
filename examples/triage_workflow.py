"""Demo: run a triage assessment for a patient presenting with symptoms."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestrator import Orchestrator


async def main() -> None:
    orchestrator = Orchestrator(use_llm=False)

    context = AgentContext(
        patient_id="demo-001",
        symptoms=["fever", "cough"],
    )

    result = await orchestrator.run(
        query="I've had a fever and cough for 3 days. Should I see a doctor?",
        agent="triage",
        context=context,
    )

    print("=" * 60)
    print("TRIAGE WORKFLOW DEMO")
    print("=" * 60)
    print(result.content)
    print(f"\nConfidence: {result.confidence:.0%}")
    print(f"Care Level: {result.metadata.get('care_level', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
