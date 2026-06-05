"""Provider directory and coordination (Layer 5)."""

from typing import Any


async def lookup_provider(npi: str | None = None, name: str | None = None) -> dict[str, Any]:
    return {
        "provider_id": "provider-101",
        "npi": npi or "1234567890",
        "name": name or "City Medical Group",
        "specialty": "Primary Care",
        "network_status": "in_network",
        "accepting_new_patients": True,
    }


async def coordinate_referral(
    member_id: str,
    from_provider_npi: str,
    to_specialty: str,
) -> dict[str, Any]:
    return {
        "referral_id": f"REF-{member_id[-3:]}-001",
        "member_id": member_id,
        "from_provider_npi": from_provider_npi,
        "to_specialty": to_specialty,
        "status": "initiated",
    }
