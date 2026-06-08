"""Layer 2 — FastAPI application / API gateway."""

from typing import Any, Literal

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestration import GraphOrchestrator
from healthcare_agents.use_cases import (
    AppointmentBookingUseCase,
    ClaimsRefundUseCase,
    ClaimsTroubleshootingUseCase,
)

UseCaseId = Literal["appointment_booking", "claims_refund", "claims_troubleshooting"]


class HealthcareAPIService:
    """Application layer — orchestrates use cases and agent runs behind API gateway."""

    def __init__(self):
        self.orchestrator = GraphOrchestrator()
        self.use_cases = {
            "appointment_booking": AppointmentBookingUseCase(self.orchestrator),
            "claims_refund": ClaimsRefundUseCase(self.orchestrator),
            "claims_troubleshooting": ClaimsTroubleshootingUseCase(self.orchestrator),
        }

    async def run_agent(
        self,
        query: str,
        *,
        member_id: str | None = None,
        role: str = "member",
        agent: str = "auto",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ctx = AgentContext(member_id=member_id, role=role, metadata=metadata or {})
        result = await self.orchestrator.run(query, agent=agent, context=ctx)  # type: ignore[arg-type]
        return {
            "orchestrator": "graph_orchestrator",
            "agent": result.agent_name,
            "content": result.content,
            "confidence": result.confidence,
            "agents_invoked": result.metadata.get("agents_invoked", []),
            "mcp_tools_used": result.metadata.get("mcp_tools_used", []),
            "metadata": result.metadata,
        }

    async def run_use_case(
        self,
        use_case_id: UseCaseId,
        query: str,
        *,
        member_id: str | None = None,
        role: str = "member",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        uc = self.use_cases[use_case_id]
        ctx = AgentContext(member_id=member_id, role=role, metadata=metadata or {})
        result = await uc.execute(query, context=ctx)
        return {
            "use_case": result.use_case,
            "status": result.status,
            "final_message": result.final_message,
            "steps": [
                {"step": s.step, "name": s.name, "agent": s.agent, "status": s.status}
                for s in result.steps
            ],
            "metadata": result.metadata,
        }

    def health(self) -> dict[str, str]:
        return {"status": "ok", "service": "classroom-Healthcare-Medicaid-customer-service-agenticAI"}


def create_app():
    """Create FastAPI app (requires `pip install -e '.[api]'`)."""
    import os
    try:
        from fastapi import Depends, FastAPI, Header, HTTPException
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise ImportError("Install API extras: pip install -e '.[api]'") from exc

    from healthcare_agents.api.auth import AuthService
    from healthcare_agents.experience.dashboard import DashboardAPI

    app = FastAPI(
        title="Classroom Healthcare Medicaid Customer Service Agentic AI",
        description="Layer 2 Application / API Gateway",
        version="0.3.0",
    )
    service = HealthcareAPIService()
    auth_service = AuthService()
    dashboard_api = DashboardAPI(
        memory=service.orchestrator.persistent_memory,
        hitl=service.orchestrator.hitl
    )

    class ChatRequest(BaseModel):
        query: str
        member_id: str | None = None
        metadata: dict[str, Any] = Field(default_factory=dict)

    class QueryRequest(BaseModel):
        query: str
        member_id: str | None = None
        agent: str = "auto"
        metadata: dict[str, Any] = Field(default_factory=dict)

    class UseCaseRequest(BaseModel):
        query: str
        member_id: str | None = None
        metadata: dict[str, Any] = Field(default_factory=dict)

    def require_auth(x_api_key: str | None = Header(default=None)):
        auth = auth_service.authenticate(x_api_key)
        if not auth:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return auth

    @app.get("/health")
    async def health():
        return service.health()

    @app.post("/v1/chat")
    async def chat(body: ChatRequest, auth=Depends(require_auth)):
        """Prompt-only entry — orchestrator routes to agents and MCP tools."""
        return await service.run_agent(
            body.query,
            member_id=body.member_id or auth.subject,
            role=auth.role,
            agent="auto",
            metadata=body.metadata,
        )

    @app.post("/v1/agents/run")
    async def run_agent(body: QueryRequest, auth=Depends(require_auth)):
        return await service.run_agent(
            body.query,
            member_id=body.member_id or auth.subject,
            role=auth.role,
            agent=body.agent,
            metadata=body.metadata,
        )

    @app.post("/v1/use-cases/{use_case_id}")
    async def run_use_case(use_case_id: UseCaseId, body: UseCaseRequest, auth=Depends(require_auth)):
        return await service.run_use_case(
            use_case_id,
            body.query,
            member_id=body.member_id or auth.subject,
            role=auth.role,
            metadata=body.metadata,
        )

    # Dashboard routes
    @app.get("/v1/dashboard/checkpoints")
    async def get_checkpoints(auth=Depends(require_auth)):
        return dashboard_api.get_pending_checkpoints()

    @app.get("/v1/dashboard/handoffs")
    async def get_handoffs(auth=Depends(require_auth)):
        return dashboard_api.get_pending_handoffs()

    @app.post("/v1/dashboard/checkpoints/approve/{case_id}")
    async def approve_checkpoint(case_id: str, auth=Depends(require_auth)):
        res = dashboard_api.approve_checkpoint(case_id)
        if not res:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        return res

    @app.post("/v1/dashboard/handoffs/acknowledge/{escalation_id}")
    async def acknowledge_handoff(escalation_id: str, auth=Depends(require_auth)):
        res = dashboard_api.acknowledge_handoff(escalation_id)
        if res.get("error") == "not_found":
            raise HTTPException(status_code=404, detail="Handoff not found")
        return res

    @app.get("/v1/dashboard/cases/{case_id}")
    async def get_case(case_id: str, auth=Depends(require_auth)):
        res = dashboard_api.get_case(case_id)
        if not res:
            raise HTTPException(status_code=404, detail="Case not found")
        return res

    # Static assets serving
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(static_dir, "index.html"))

    return app
