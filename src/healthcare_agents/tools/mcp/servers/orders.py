"""MCP Server 4 — Order Management."""

from healthcare_agents.tools.orders import cancel_order, create_order, track_order, update_order

SERVER_NAME = "order_management"
TOOLS = {
    "get_order_status": track_order,
    "modify_order": update_order,
    "cancel_order": cancel_order,
    "create_order": create_order,
}
