"""Chat interface handler for member and provider interactions (Layer 1)."""

from dataclasses import dataclass
from uuid import uuid4

from healthcare_agents.agents.base import AgentContext, AgentResult
from healthcare_agents.orchestration import GraphOrchestrator


@dataclass
class ChatSession:
    session_id: str
    member_id: str | None = None
    role: str = "member"


class ChatInterface:
    """Conversational entry point for guided healthcare workflows."""

    def __init__(self, orchestrator: GraphOrchestrator | None = None):
        self.orchestrator = orchestrator or GraphOrchestrator()

    def create_session(self, member_id: str | None = None, role: str = "member") -> ChatSession:
        return ChatSession(session_id=f"sess-{uuid4().hex[:12]}", member_id=member_id, role=role)

    async def send_message(
        self,
        session: ChatSession,
        message: str,
        context: AgentContext | None = None,
    ) -> AgentResult:
        ctx = context or AgentContext(
            member_id=session.member_id,
            session_id=session.session_id,
            role=session.role,
        )
        ctx.session_id = session.session_id
        ctx.member_id = session.member_id or ctx.member_id
        ctx.role = session.role
        return await self.orchestrator.run(message, agent="auto", context=ctx)
