"""MCP server registry — standardized tool servers."""

from dataclasses import dataclass
from typing import Any

from healthcare_agents.tools.mcp.servers import (
    billing,
    diagnostics,
    identity,
    notifications_server,
    orders,
    scheduling,
)


@dataclass
class MCPServer:
    name: str
    description: str
    tools: dict[str, Any]


MCP_SERVERS: dict[str, MCPServer] = {
    identity.SERVER_NAME: MCPServer(
        name=identity.SERVER_NAME,
        description="Customer & Identity — profiles and verification",
        tools=identity.TOOLS,
    ),
    scheduling.SERVER_NAME: MCPServer(
        name=scheduling.SERVER_NAME,
        description="Service & Scheduling — appointments and availability",
        tools=scheduling.TOOLS,
    ),
    billing.SERVER_NAME: MCPServer(
        name=billing.SERVER_NAME,
        description="Billing & Refunds — eligibility, refunds, invoices",
        tools=billing.TOOLS,
    ),
    orders.SERVER_NAME: MCPServer(
        name=orders.SERVER_NAME,
        description="Order Management — lifecycle operations",
        tools=orders.TOOLS,
    ),
    diagnostics.SERVER_NAME: MCPServer(
        name=diagnostics.SERVER_NAME,
        description="Operations Diagnostics — audit, policy checks, retries",
        tools=diagnostics.TOOLS,
    ),
    notifications_server.SERVER_NAME: MCPServer(
        name=notifications_server.SERVER_NAME,
        description="Notifications & Documents — secure comms and document store",
        tools=notifications_server.TOOLS,
    ),
}


def list_servers() -> list[str]:
    return list(MCP_SERVERS.keys())


def get_server(name: str) -> MCPServer | None:
    return MCP_SERVERS.get(name)
