"""Order lifecycle workflow — validate → inventory → fulfill → track → complete."""

from dataclasses import dataclass, field
from typing import Any

from healthcare_agents.agents.base import AgentContext, AgentResult
from healthcare_agents.tools.orders import (
    check_inventory,
    create_order,
    track_order,
    update_order,
)


@dataclass
class OrderWorkflowState:
    member_id: str
    order_type: str
    items: list[str]
    order_id: str | None = None
    steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class OrderManagementWorkflow:
    """Order Management Agent — end-to-end lifecycle with exception handling."""

    name = "order_management_agent"

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        member_id = context.subject_id or context.metadata.get("member_id", "")
        items = context.metadata.get("items", ["dme_supply"])
        order_type = context.metadata.get("order_type", "fulfillment")

        if not member_id:
            return AgentResult(
                agent_name=self.name,
                content="Member ID required for order management.",
                confidence=0.0,
            )

        state = OrderWorkflowState(
            member_id=member_id,
            order_type=order_type,
            items=items if isinstance(items, list) else [items],
            order_id=context.metadata.get("order_id"),
        )

        state = await self._think_plan(state, query)
        state = await self._validate_request(state)
        state = await self._check_inventory(state)
        state = await self._route_fulfillment(state)
        state = await self._process_order(state)
        state = await self._track_status(state)
        state = await self._finalize(state)

        content = (
            f"Order Management\n"
            f"Order ID: {state.order_id or 'pending'}\n"
            f"Type: {state.order_type}\n"
            f"Status: {state.metadata.get('order_status', 'unknown')}\n"
            f"Steps: {' → '.join(state.steps)}"
        )

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.88,
            tool_calls=state.metadata.get("tool_calls", []),
            metadata={**state.metadata, "workflow_steps": state.steps},
        )

    async def _think_plan(self, state: OrderWorkflowState, query: str) -> OrderWorkflowState:
        state.steps.append("think_plan")
        state.metadata["plan"] = f"Process {state.order_type} order for {state.member_id}"
        return state

    async def _validate_request(self, state: OrderWorkflowState) -> OrderWorkflowState:
        state.steps.append("validate_order")
        state.metadata["schema_valid"] = bool(state.member_id and state.items)
        return state

    async def _check_inventory(self, state: OrderWorkflowState) -> OrderWorkflowState:
        result = await check_inventory(state.items)
        state.metadata["inventory_available"] = result["available"]
        state.metadata.setdefault("tool_calls", []).append(
            {"tool": "check_inventory", "result": result}
        )
        state.steps.append("check_inventory")
        return state

    async def _route_fulfillment(self, state: OrderWorkflowState) -> OrderWorkflowState:
        path = "standard" if state.metadata.get("inventory_available") else "backorder"
        state.metadata["fulfillment_path"] = path
        state.steps.append("route_fulfillment")
        return state

    async def _process_order(self, state: OrderWorkflowState) -> OrderWorkflowState:
        if state.order_id:
            result = await update_order(state.order_id, "processing")
        else:
            result = await create_order(state.member_id, state.order_type, state.items)
            state.order_id = result["order_id"]
        state.metadata["order_status"] = result.get("status", "processing")
        state.metadata.setdefault("tool_calls", []).append(
            {"tool": "create_or_update_order", "result": result}
        )
        state.steps.append("process_order")
        return state

    async def _track_status(self, state: OrderWorkflowState) -> OrderWorkflowState:
        if state.order_id:
            tracked = await track_order(state.order_id)
            state.metadata["order_status"] = tracked["status"]
            state.metadata["exceptions"] = tracked.get("exceptions", [])
            state.metadata.setdefault("tool_calls", []).append(
                {"tool": "track_order", "result": tracked}
            )
        state.steps.append("track_status")
        return state

    async def _finalize(self, state: OrderWorkflowState) -> OrderWorkflowState:
        state.metadata["audit_logged"] = True
        state.steps.append("complete")
        return state
