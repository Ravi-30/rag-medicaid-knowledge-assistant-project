"""Demo: Use Case 2 — Claims Refund / Adjustment Request."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.use_cases import ClaimsRefundUseCase


async def main() -> None:
    use_case = ClaimsRefundUseCase()
    ctx = AgentContext(
        member_id="member-001",
        role="member",
        metadata={
            "claim_id": "CLM-ABC123",
            "amount_usd": 250.0,
            "user_confirmed": True,
        },
    )

    result = await use_case.execute(
        "I was charged $250 for a lab test that my insurance should have covered. I'd like a refund.",
        context=ctx,
    )

    print("=" * 60)
    print("USE CASE 2: CLAIMS REFUND")
    print("=" * 60)
    print(f"Status: {result.status}\n")
    for step in result.steps:
        print(f"  [{step.step}] {step.name} — {step.status}")
    print(f"\n{result.final_message}")


if __name__ == "__main__":
    asyncio.run(main())
