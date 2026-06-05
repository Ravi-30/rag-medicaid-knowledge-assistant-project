"""Context engineering pipeline: Select → Compress → Structure → Filter."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EngineeredContext:
    """Structured context ready for agent reasoning."""

    snippets: list[str] = field(default_factory=list)
    structured: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    token_estimate: int = 0


class ContextEngineeringPipeline:
    """Actively engineers context — not just retrieval."""

    def __init__(self, max_snippets: int = 5, max_chars: int = 2000):
        self.max_snippets = max_snippets
        self.max_chars = max_chars

    def run(
        self,
        rag_results: list[str],
        knowledge_graph: dict[str, Any] | None = None,
        session_history: list[str] | None = None,
        query: str = "",
    ) -> EngineeredContext:
        selected = self._select(rag_results, session_history, query)
        compressed = self._compress(selected)
        structured = self._structure(compressed, knowledge_graph)
        filtered = self._filter(structured, query)
        return filtered

    def _select(
        self,
        rag_results: list[str],
        session_history: list[str] | None,
        query: str,
    ) -> list[str]:
        selected = list(rag_results[: self.max_snippets])
        if session_history:
            selected.extend(session_history[-2:])
        if query:
            query_words = set(query.lower().split())
            selected.sort(
                key=lambda s: sum(1 for w in query_words if w in s.lower()),
                reverse=True,
            )
        return selected[: self.max_snippets]

    def _compress(self, snippets: list[str]) -> list[str]:
        compressed: list[str] = []
        total = 0
        for snippet in snippets:
            if total + len(snippet) > self.max_chars:
                remaining = self.max_chars - total
                if remaining > 100:
                    compressed.append(snippet[:remaining] + "...")
                break
            compressed.append(snippet)
            total += len(snippet)
        return compressed

    def _structure(
        self,
        snippets: list[str],
        knowledge_graph: dict[str, Any] | None,
    ) -> EngineeredContext:
        sources = [s.split(":")[0] for s in snippets if ":" in s]
        return EngineeredContext(
            snippets=snippets,
            structured={
                "policy_docs": snippets,
                "member_graph": knowledge_graph or {},
            },
            sources=sources,
            token_estimate=sum(len(s.split()) for s in snippets),
        )

    def _filter(self, ctx: EngineeredContext, query: str) -> EngineeredContext:
        lower = query.lower()
        if "phi" in lower or "ssn" in lower:
            ctx.snippets = [
                s for s in ctx.snippets if "[REDACTED" not in s or "policy" in s.lower()
            ]
        return ctx
