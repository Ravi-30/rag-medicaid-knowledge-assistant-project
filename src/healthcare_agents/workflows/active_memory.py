"""Active memory management workflow — summarize, conflict detect, prune."""

from dataclasses import dataclass, field
from typing import Any

from healthcare_agents.agents.base import AgentContext, AgentResult
from healthcare_agents.context import PersistentMemory, SessionMemory
from healthcare_agents.context.memory import MemoryEntry
from healthcare_agents.schemas.memory import MemoryArtifact


@dataclass
class ActiveMemoryState:
    context: AgentContext
    query: str
    artifact: MemoryArtifact | None = None
    steps: list[str] = field(default_factory=list)


class ActiveMemoryWorkflow:
    """Memory & Context Agent — active memory management across operations."""

    name = "memory_context_agent"

    def __init__(
        self,
        session_memory: SessionMemory | None = None,
        persistent_memory: PersistentMemory | None = None,
        max_context_chars: int = 2000,
    ):
        self.session_memory = session_memory or SessionMemory()
        self.persistent_memory = persistent_memory or PersistentMemory()
        self.max_context_chars = max_context_chars

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        state = ActiveMemoryState(context=context, query=query)
        state = await self._summarize_and_store(state)
        state = await self._detect_conflicts(state)
        state = await self._prune_context(state)
        state = await self._persist_delta(state)

        assert state.artifact is not None
        content = (
            f"Memory & Context — Active Management\n"
            f"Session: {context.session_id or 'N/A'} | Case: {context.case_id or 'N/A'}\n"
            f"Conflicts: {len(state.artifact.conflicts_detected)}\n"
            f"Pruned tokens (est.): {state.artifact.pruned_tokens}\n\n"
            f"Summarized Context:\n{state.artifact.summarized_context[:500]}"
        )

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.9,
            metadata={
                "artifact": state.artifact.model_dump(),
                "workflow_steps": state.steps,
            },
        )

    async def _summarize_and_store(self, state: ActiveMemoryState) -> ActiveMemoryState:
        ctx = state.context
        parts: list[str] = []

        if ctx.session_id:
            history = self.session_memory.get_history(ctx.session_id, limit=10)
            if history:
                parts.append(
                    "Recent session: "
                    + "; ".join(f"{e.role}: {e.content[:80]}" for e in history[-3:])
                )

        if ctx.case_id:
            case = self.persistent_memory.get_case(ctx.case_id)
            if case:
                parts.append(f"Case {case.case_id} ({case.status}): {case.workflow_type}")

        if ctx.rag_context:
            parts.append(f"RAG: {len(ctx.rag_context)} policy snippets loaded")

        if ctx.member_id:
            parts.append(f"Member profile key: {ctx.member_id}")

        summary = "\n".join(parts) or "No prior context available."
        state.artifact = MemoryArtifact(
            summarized_context=summary,
            retrieval_index=[f"session:{ctx.session_id}", f"case:{ctx.case_id}"]
            if ctx.session_id or ctx.case_id
            else [],
        )
        state.steps.append("summarize_and_store")
        return state

    async def _detect_conflicts(self, state: ActiveMemoryState) -> ActiveMemoryState:
        assert state.artifact is not None
        ctx = state.context
        conflicts: list[str] = []

        eligible_meta = ctx.metadata.get("eligible")
        if eligible_meta is False and "coverage" in state.query.lower():
            conflicts.append("Member marked ineligible but query references active coverage.")

        if ctx.metadata.get("claim_id") and ctx.metadata.get("order_id"):
            conflicts.append("Both claim and order IDs present — verify workflow scope.")

        state.artifact.conflicts_detected = conflicts
        state.steps.append("detect_conflicts")
        return state

    async def _prune_context(self, state: ActiveMemoryState) -> ActiveMemoryState:
        assert state.artifact is not None
        ctx = state.context
        full_len = len(state.artifact.summarized_context) + sum(
            len(s) for s in ctx.rag_context
        )
        if full_len > self.max_context_chars:
            pruned = state.artifact.summarized_context[: self.max_context_chars]
            state.artifact.summarized_context = pruned + "..."
            state.artifact.pruned_tokens = (full_len - self.max_context_chars) // 4
            ctx.rag_context = ctx.rag_context[:3]
        state.steps.append("prune_context")
        return state

    async def _persist_delta(self, state: ActiveMemoryState) -> ActiveMemoryState:
        assert state.artifact is not None
        ctx = state.context
        delta = {
            "last_query": state.query[:200],
            "conflicts": state.artifact.conflicts_detected,
            "index": state.artifact.retrieval_index,
        }
        state.artifact.memory_delta = delta

        if ctx.session_id:
            self.session_memory.append(
                ctx.session_id,
                role="system",
                content=f"Memory update: {state.artifact.summarized_context[:150]}",
                agent=self.name,
            )

        if ctx.case_id:
            self.persistent_memory.update_case(
                ctx.case_id,
                entry=MemoryEntry(role="system", content="Active memory context refreshed"),
                metadata={"memory_delta": delta},
            )

        state.steps.append("persist_delta")
        return state
