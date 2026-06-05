"""MCP Server 3 — Billing & Refunds."""

from healthcare_agents.tools.billing import (
    check_refund_eligibility,
    process_refund,
    track_finance,
)

SERVER_NAME = "billing_refunds"

async def fetch_invoice(member_id: str, claim_id: str | None = None) -> dict:
    return {
        "member_id": member_id,
        "claim_id": claim_id,
        "invoice_total_usd": 250.0,
        "status": "issued",
    }


TOOLS = {
    "check_refund_eligibility": check_refund_eligibility,
    "process_refund": process_refund,
    "fetch_invoice": fetch_invoice,
    "track_finance": track_finance,
}
