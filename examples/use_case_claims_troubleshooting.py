"""Demo: Use Case 3 — Claims & Eligibility Troubleshooting."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.use_cases import ClaimsTroubleshootingUseCase


async def main() -> None:
    use_case = ClaimsTroubleshootingUseCase()
    ctx = AgentContext(
        member_id="member-001",
        role="member",
        metadata={"claim_id": "CLM-DENIED-001"},
    )

    result = await use_case.execute(
        "My claim was denied and I don't understand why. It should be covered.",
        context=ctx,
    )

    print("=" * 60)
    print("USE CASE 3: CLAIMS TROUBLESHOOTING")
    print("=" * 60)
    print(f"Status: {result.status}\n")
    for step in result.steps:
        print(f"  [{step.step}] {step.name} — {step.status}")
    print(f"\nRoot cause: {result.metadata.get('root_cause')}")
    print(f"\n{result.final_message}")


if __name__ == "__main__":
    asyncio.run(main())
