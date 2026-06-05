"""Eligibility and benefits verification (Layer 5)."""

from typing import Any


async def verify_eligibility(member_id: str, service_date: str | None = None) -> dict[str, Any]:
    active = member_id.startswith("member-") or member_id.startswith("M")
    return {
        "member_id": member_id,
        "eligible": active,
        "plan": "Medicaid Plus" if active else None,
        "coverage_status": "active" if active else "inactive",
        "service_date": service_date,
        "benefits": {
            "medical": active,
            "pharmacy": active,
            "behavioral_health": active,
        },
    }
