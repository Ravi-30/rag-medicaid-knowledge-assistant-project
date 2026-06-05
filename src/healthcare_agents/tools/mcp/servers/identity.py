"""MCP Server 1 — Customer & Identity."""

from healthcare_agents.tools.eligibility import verify_eligibility

SERVER_NAME = "customer_identity"
TOOLS = {
    "get_customer_profile": verify_eligibility,
    "verify_identity": verify_eligibility,
}
