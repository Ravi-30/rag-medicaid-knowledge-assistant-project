"""RAG engine client for policy and operational knowledge retrieval (Layer 4)."""

from dataclasses import dataclass
from typing import Any

from healthcare_agents.config import settings


@dataclass
class RetrievalResult:
    content: str
    source: str
    score: float
    metadata: dict[str, Any]


class RAGEngine:
    """Semantic retrieval over healthcare policy and operational documents.

    Production deployments connect to Milvus (or another vector store) via
    ``RAG_BASE_URL``. This implementation uses an in-memory corpus for dev/test.
    """

    _DEV_CORPUS: list[dict[str, Any]] = [
        {
            "source": "medicaid_eligibility_manual.pdf",
            "topic": "eligibility",
            "content": (
                "Medicaid eligibility requires verified residency, income within "
                "state thresholds, and citizenship or qualified immigration status."
            ),
        },
        {
            "source": "prior_auth_guidelines.pdf",
            "topic": "prior_authorization",
            "content": (
                "Prior authorization is required for elective MRI, specialty biologics, "
                "and inpatient admissions. Submit clinical documentation within 14 days."
            ),
        },
        {
            "source": "claims_processing_sop.pdf",
            "topic": "claims",
            "content": (
                "Claims must include valid member ID, provider NPI, CPT/HCPCS codes, "
                "and date of service. Duplicate submissions are auto-rejected."
            ),
        },
        {
            "source": "provider_network_policy.pdf",
            "topic": "provider",
            "content": (
                "In-network providers require credentialing verification. "
                "Out-of-network referrals need medical necessity documentation."
            ),
        },
    ]

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.rag_base_url).rstrip("/")

    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        topic: str | None = None,
    ) -> list[RetrievalResult]:
        if self.base_url and self.base_url != "memory":
            return await self._retrieve_remote(query, top_k, topic)
        return self._retrieve_local(query, top_k, topic)

    async def _retrieve_remote(
        self, query: str, top_k: int, topic: str | None
    ) -> list[RetrievalResult]:
        # Placeholder for Milvus / enterprise RAG HTTP API integration.
        return self._retrieve_local(query, top_k, topic)

    def _retrieve_local(
        self, query: str, top_k: int, topic: str | None
    ) -> list[RetrievalResult]:
        lower = query.lower()
        scored: list[tuple[float, dict[str, Any]]] = []

        for doc in self._DEV_CORPUS:
            if topic and doc["topic"] != topic:
                continue
            overlap = sum(1 for word in lower.split() if word in doc["content"].lower())
            if overlap or (topic and doc["topic"] == topic):
                scored.append((overlap + (2 if topic == doc["topic"] else 0), doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[RetrievalResult] = []
        for score, doc in scored[:top_k]:
            results.append(
                RetrievalResult(
                    content=doc["content"],
                    source=doc["source"],
                    score=min(1.0, score / 5),
                    metadata={"topic": doc["topic"]},
                )
            )
        return results
