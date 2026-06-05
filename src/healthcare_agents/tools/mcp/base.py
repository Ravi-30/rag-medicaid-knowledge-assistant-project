"""MCP tool foundation — strong typing, contracts, idempotency, audit, retry."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class ToolContract:
    name: str
    description: str
    category: str
    required_fields: list[str] = field(default_factory=list)
    idempotent: bool = True


@dataclass
class ToolResult:
    success: bool
    data: dict[str, Any]
    error: str | None = None
    idempotency_key: str | None = None


class MCPTool:
    """Unified MCP tool wrapper with validation, retry, and audit hooks."""

    def __init__(
        self,
        contract: ToolContract,
        handler: Callable[..., Awaitable[dict[str, Any]]],
        audit_callback: Callable[[str, dict[str, Any]], None] | None = None,
        max_retries: int = 2,
        timeout_seconds: float = 30.0,
    ):
        self.contract = contract
        self.handler = handler
        self.audit_callback = audit_callback
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self._idempotency_cache: dict[str, ToolResult] = {}

    async def invoke(
        self,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> ToolResult:
        missing = [f for f in self.contract.required_fields if not payload.get(f)]
        if missing:
            return ToolResult(
                success=False,
                data={},
                error=f"Missing required fields: {', '.join(missing)}",
            )

        key = idempotency_key or payload.get("idempotency_key") or str(uuid4())
        if self.contract.idempotent and key in self._idempotency_cache:
            cached = self._idempotency_cache[key]
            logger.info("MCP tool %s idempotent hit: %s", self.contract.name, key)
            return cached

        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            try:
                data = await asyncio.wait_for(
                    self.handler(**payload),
                    timeout=self.timeout_seconds,
                )
                result = ToolResult(success=True, data=data, idempotency_key=key)
                if self.contract.idempotent:
                    self._idempotency_cache[key] = result
                if self.audit_callback:
                    self.audit_callback(self.contract.name, {"payload": payload, "success": True})
                return result
            except TimeoutError:
                last_error = f"Timeout after {self.timeout_seconds}s"
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "MCP tool %s attempt %d failed: %s",
                    self.contract.name,
                    attempt + 1,
                    last_error,
                )
            if attempt < self.max_retries:
                await asyncio.sleep(0.5 * (attempt + 1))

        if self.audit_callback:
            self.audit_callback(
                self.contract.name, {"payload": payload, "success": False, "error": last_error}
            )
        return ToolResult(success=False, data={}, error=last_error, idempotency_key=key)
