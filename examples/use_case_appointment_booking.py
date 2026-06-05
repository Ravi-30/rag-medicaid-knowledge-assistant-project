"""Demo: Use Case 1 — Healthcare Appointment Booking."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.use_cases import AppointmentBookingUseCase


async def main() -> None:
    use_case = AppointmentBookingUseCase()
    ctx = AgentContext(
        member_id="member-001",
        role="member",
        metadata={"user_confirmed": True, "service_type": "primary_care"},
    )

    result = await use_case.execute(
        "I need an appointment for my back pain next week",
        context=ctx,
    )

    print("=" * 60)
    print("USE CASE 1: APPOINTMENT BOOKING")
    print("=" * 60)
    print(f"Status: {result.status}\n")
    for step in result.steps:
        print(f"  [{step.step}] {step.name} ({step.agent}) — {step.status}")
    print(f"\n{result.final_message}")


if __name__ == "__main__":
    asyncio.run(main())
