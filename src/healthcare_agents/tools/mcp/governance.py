"""MCP governance model — safe execution boundaries for governed tool calls."""

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from healthcare_agents.tools.mcp.base import MCPTool, ToolContract, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class GovernanceDecision:
    allowed: bool
    reason: str = ""
    masked_payload: dict[str, Any] = field(default_factory=dict)


class MCPGovernanceLayer:
    """Wraps MCP tools with validation, policy, timeouts, circuit breaker, and audit."""

    def __init__(
        self,
        policy_check: Callable[[str, dict[str, Any]], GovernanceDecision] | None = None,
        audit_callback: Callable[[str, dict[str, Any]], None] | None = None,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
    ):
        self.policy_check = policy_check or self._default_policy
        self.audit_callback = audit_callback
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failure_counts: dict[str, int] = {}
        self._circuit_open_until: dict[str, float] = {}

    def _default_policy(self, tool_name: str, payload: dict[str, Any]) -> GovernanceDecision:
        return GovernanceDecision(allowed=True, masked_payload=payload)

    def _circuit_open(self, tool_name: str) -> bool:
        until = self._circuit_open_until.get(tool_name, 0)
        return time.monotonic() < until

    def _record_failure(self, tool_name: str) -> None:
        count = self._failure_counts.get(tool_name, 0) + 1
        self._failure_counts[tool_name] = count
        if count >= self.failure_threshold:
            self._circuit_open_until[tool_name] = time.monotonic() + self.cooldown_seconds
            logger.warning("MCP circuit open for %s", tool_name)

    def _record_success(self, tool_name: str) -> None:
        self._failure_counts[tool_name] = 0

    async def invoke(
        self,
        tool: MCPTool,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> ToolResult:
        name = tool.contract.name
        if self._circuit_open(name):
            return ToolResult(success=False, data={}, error=f"Circuit open for {name}")

        decision = self.policy_check(name, payload)
        if not decision.allowed:
            if self.audit_callback:
                self.audit_callback(name, {"blocked": True, "reason": decision.reason})
            return ToolResult(success=False, data={}, error=decision.reason)

        result = await tool.invoke(decision.masked_payload or payload, idempotency_key)
        if result.success:
            self._record_success(name)
        else:
            self._record_failure(name)

        if self.audit_callback:
            self.audit_callback(
                name,
                {
                    "success": result.success,
                    "idempotency_key": result.idempotency_key,
                    "error": result.error,
                },
            )
        return result

    def wrap_handler(
        self,
        contract: ToolContract,
        handler: Callable[..., Awaitable[dict[str, Any]]],
        audit_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> MCPTool:
        """Create a governed MCPTool instance."""
        return MCPTool(contract, handler, audit_callback=audit_callback or self.audit_callback)
