from typing import Any

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.agents.reasoning import ReasoningAgent
from healthcare_agents.context import PersistentMemory, SessionMemory


class MemoryContextAgent(ReasoningAgent):
    """Assembles and persists workflow context across sessions and cases."""

    name = "memory_context_agent"
    description = (
        "You manage session memory, case history, and context assembly "
        "for long-running healthcare workflows."
    )

    def __init__(
        self,
        llm_client=None,
        session_memory: SessionMemory | None = None,
        persistent_memory: PersistentMemory | None = None,
    ):
        super().__init__(llm_client)
        self.session_memory = session_memory or SessionMemory()
        self.persistent_memory = persistent_memory or PersistentMemory()

    async def _act(
        self, context: AgentContext, query: str, thought: dict[str, Any]
    ) -> dict[str, Any]:
        session_turns = 0
        case_status = "none"

        if context.session_id:
            session_turns = len(self.session_memory.get_history(context.session_id))

        if context.case_id:
            case = self.persistent_memory.get_case(context.case_id)
            if case:
                case_status = case.status

        content = (
            f"Memory & Context\n"
            f"Session ID: {context.session_id or 'N/A'}\n"
            f"Case ID: {context.case_id or 'N/A'}\n"
            f"Session Turns: {session_turns}\n"
            f"Case Status: {case_status}\n"
            f"RAG Snippets Loaded: {len(context.rag_context)}"
        )
        return {
            "content": content,
            "confidence": 0.88,
            "metadata": {
                "session_turns": session_turns,
                "case_status": case_status,
            },
        }
