"""API gateway for secure routing to enterprise systems (Layer 5)."""

from typing import Any

import httpx

from healthcare_agents.config import settings


class APIGateway:
    """Routes tool calls through a central gateway with auth and throttling hooks."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or settings.api_gateway_url).rstrip("/")
        self.api_key = api_key or settings.api_gateway_key

    async def invoke(
        self,
        service: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.base_url or self.base_url == "local":
            return {
                "service": service,
                "path": path,
                "status": "mock_ok",
                "payload": payload or {},
            }

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/{service}/{path}",
                json=payload or {},
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
