"""Retrieval evaluation metrics — precision@k and recall@k."""

from dataclasses import dataclass


@dataclass
class RetrievalMetrics:
    precision_at_k: float
    recall_at_k: float
    k: int
    retrieved_count: int
    relevant_count: int
    hits: int


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Fraction of top-k retrieved items that are relevant."""
    if k <= 0:
        return 0.0
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / len(top_k)


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Fraction of relevant items found in top-k retrieved results."""
    if k <= 0 or not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / len(relevant)


def evaluate_retrieval(
    retrieved: list[str],
    relevant: set[str],
    k: int = 5,
) -> RetrievalMetrics:
    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return RetrievalMetrics(
        precision_at_k=precision_at_k(retrieved, relevant, k),
        recall_at_k=recall_at_k(retrieved, relevant, k),
        k=k,
        retrieved_count=len(top_k),
        relevant_count=len(relevant),
        hits=hits,
    )
