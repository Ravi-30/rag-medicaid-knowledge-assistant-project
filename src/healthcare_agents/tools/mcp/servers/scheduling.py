"""MCP Server 2 — Service & Scheduling."""

from healthcare_agents.tools.scheduling import (
    book_appointment,
    check_availability,
    reschedule_appointment,
)

SERVER_NAME = "service_scheduling"
TOOLS = {
    "check_availability": check_availability,
    "book_appointment": book_appointment,
    "reschedule_appointment": reschedule_appointment,
}
