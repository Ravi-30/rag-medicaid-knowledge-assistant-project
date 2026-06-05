"""MCP Server 6 — Notifications & Documents."""

from healthcare_agents.tools.mcp.servers import notifications as notification_tools

SERVER_NAME = "notifications"
TOOLS = {
    "send_notification": notification_tools.send_notification,
    "store_document": notification_tools.store_document,
    "write_audit_event": notification_tools.write_audit_event,
}
