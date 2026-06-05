"""Demo: Service & Appointment hybrid scheduling workflow."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestration import GraphOrchestrator


async def main() -> None:
    orchestrator = GraphOrchestrator()

    # Step 1: Triage
    triage_ctx = AgentContext(member_id="member-001", role="member")
    triage = await orchestrator.run(
        "I need to schedule a primary care appointment",
        agent="triage_routing",
        context=triage_ctx,
    )
    print("=" * 60)
    print("TRIAGE")
    print("=" * 60)
    print(triage.content)

    # Step 2: Fetch availability (awaiting confirmation)
    appt_ctx = AgentContext(member_id="member-001", role="member")
    pending = await orchestrator.run(
        "Schedule primary care appointment",
        agent="service_appointment",
        context=appt_ctx,
    )
    print("\n" + "=" * 60)
    print("APPOINTMENT — AWAITING CONFIRMATION")
    print("=" * 60)
    print(pending.content)

    # Step 3: Confirm and book
    slots = pending.metadata.get("available_slots", [])
    if slots:
        confirmed_ctx = AgentContext(
            member_id="member-001",
            role="member",
            metadata={
                "selected_slot": slots[0],
                "user_confirmed": True,
                "available_slots": slots,
            },
        )
        booked = await orchestrator.run(
            "Confirm appointment booking",
            agent="service_appointment",
            context=confirmed_ctx,
        )
        print("\n" + "=" * 60)
        print("APPOINTMENT — CONFIRMED")
        print("=" * 60)
        print(booked.content)


if __name__ == "__main__":
    asyncio.run(main())
