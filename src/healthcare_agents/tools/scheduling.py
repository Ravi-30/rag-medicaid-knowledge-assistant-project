"""Service & appointment scheduling tools (MCP)."""

from datetime import date, timedelta
from typing import Any
from uuid import uuid4


async def check_availability(
    member_id: str,
    service_type: str,
    provider_npi: str | None = None,
) -> dict[str, Any]:
    base = date.today() + timedelta(days=3)
    slots = [
        (base).isoformat() + "T09:00",
        (base).isoformat() + "T11:30",
        (base + timedelta(days=1)).isoformat() + "T14:00",
    ]
    return {
        "member_id": member_id,
        "service_type": service_type,
        "provider_npi": provider_npi or "1234567890",
        "available_slots": slots,
        "network_status": "in_network",
    }


async def book_appointment(
    member_id: str,
    slot: str,
    service_type: str,
    provider_npi: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    if not confirmed:
        return {
            "status": "pending_confirmation",
            "message": "User confirmation required before booking.",
            "proposed_slot": slot,
        }
    return {
        "appointment_id": f"APT-{uuid4().hex[:8].upper()}",
        "member_id": member_id,
        "slot": slot,
        "service_type": service_type,
        "provider_npi": provider_npi or "1234567890",
        "status": "confirmed",
    }


async def reschedule_appointment(
    appointment_id: str,
    new_slot: str,
    confirmed: bool = False,
) -> dict[str, Any]:
    if not confirmed:
        return {"status": "pending_confirmation", "proposed_slot": new_slot}
    return {
        "appointment_id": appointment_id,
        "new_slot": new_slot,
        "status": "rescheduled",
    }
