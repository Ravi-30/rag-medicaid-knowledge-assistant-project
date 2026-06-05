"""MCP tool registry — unified interface for all enterprise tool categories."""

from typing import Any

from healthcare_agents.tools.billing import check_refund_eligibility, process_refund, track_finance
from healthcare_agents.tools.claims import get_claim_status
from healthcare_agents.tools.eligibility import verify_eligibility
from healthcare_agents.tools.mcp.base import MCPTool, ToolContract
from healthcare_agents.tools.orders import cancel_order, create_order, track_order
from healthcare_agents.tools.provider_directory import lookup_provider
from healthcare_agents.tools.scheduling import (
    book_appointment,
    check_availability,
    reschedule_appointment,
)


class MCPToolRegistry:
    """Registry of typed MCP tools grouped by category."""

    def __init__(self, audit_callback=None):
        self._tools: dict[str, MCPTool] = {}
        self._register_defaults(audit_callback)

    def _register_defaults(self, audit_callback) -> None:
        identity_tools = [
            (
                "get_profile",
                "Retrieve member profile",
                "identity",
                verify_eligibility,
                ["member_id"],
            ),
            (
                "verify_identity",
                "Verify member identity",
                "identity",
                verify_eligibility,
                ["member_id"],
            ),
        ]
        billing_tools = [
            (
                "check_refund_eligibility",
                "Check refund eligibility",
                "billing",
                check_refund_eligibility,
                ["member_id"],
            ),
            (
                "process_refund",
                "Process billing refund",
                "billing",
                process_refund,
                ["member_id", "claim_id", "amount_usd"],
            ),
            (
                "track_finance",
                "Track financial transaction",
                "billing",
                track_finance,
                ["transaction_id"],
            ),
        ]
        service_tools = [
            (
                "check_availability",
                "Check appointment availability",
                "service",
                check_availability,
                ["member_id", "service_type"],
            ),
            (
                "book_appointment",
                "Book healthcare appointment",
                "service",
                book_appointment,
                ["member_id", "slot", "service_type"],
            ),
            (
                "reschedule_appointment",
                "Reschedule appointment",
                "service",
                reschedule_appointment,
                ["appointment_id", "new_slot"],
            ),
        ]
        order_tools = [
            (
                "create_order",
                "Create fulfillment order",
                "order",
                create_order,
                ["member_id", "order_type", "items"],
            ),
            (
                "track_order",
                "Track order status",
                "order",
                track_order,
                ["order_id"],
            ),
            (
                "cancel_order",
                "Cancel order",
                "order",
                cancel_order,
                ["order_id", "reason"],
            ),
        ]
        case_tools = [
            (
                "get_case_status",
                "Get case or claim status",
                "case",
                get_claim_status,
                ["claim_id"],
            ),
        ]
        provider_tools = [
            (
                "verify_network",
                "Verify provider network status",
                "provider",
                lookup_provider,
                [],
            ),
            (
                "credentialing_check",
                "Check provider credentialing",
                "provider",
                lookup_provider,
                ["npi"],
            ),
        ]

        for name, desc, category, handler, required in (
            identity_tools
            + billing_tools
            + service_tools
            + order_tools
            + case_tools
            + provider_tools
        ):
            self.register(
                name,
                ToolContract(
                    name=name,
                    description=desc,
                    category=category,
                    required_fields=required,
                ),
                handler,
                audit_callback,
            )

    def register(
        self,
        name: str,
        contract: ToolContract,
        handler,
        audit_callback=None,
    ) -> None:
        self._tools[name] = MCPTool(contract, handler, audit_callback=audit_callback)

    def get(self, name: str) -> MCPTool | None:
        return self._tools.get(name)

    async def invoke(
        self,
        name: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ):
        tool = self._tools.get(name)
        if not tool:
            from healthcare_agents.tools.mcp.base import ToolResult

            return ToolResult(success=False, data={}, error=f"Unknown tool: {name}")
        return await tool.invoke(payload, idempotency_key=idempotency_key)

    def list_tools(self, category: str | None = None) -> list[ToolContract]:
        return [
            t.contract
            for t in self._tools.values()
            if category is None or t.contract.category == category
        ]
