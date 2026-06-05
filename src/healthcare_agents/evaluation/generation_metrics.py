"""Generation evaluation — ROUGE and BERTScore with optional dependencies."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GenerationMetrics:
    rouge_1: float = 0.0
    rouge_2: float = 0.0
    rouge_l: float = 0.0
    bertscore_f1: float = 0.0
    backend: str = "fallback"
    details: dict[str, Any] = field(default_factory=dict)


def _fallback_overlap(prediction: str, reference: str) -> float:
    pred_tokens = set(prediction.lower().split())
    ref_tokens = set(reference.lower().split())
    if not pred_tokens or not ref_tokens:
        return 0.0
    return len(pred_tokens & ref_tokens) / len(ref_tokens)


def rouge_scores(prediction: str, reference: str) -> dict[str, float]:
    """Compute ROUGE-1/2/L using rouge-score when installed."""
    try:
        from rouge_score import rouge_scorer

        scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        scores = scorer.score(reference, prediction)
        return {
            "rouge_1": scores["rouge1"].fmeasure,
            "rouge_2": scores["rouge2"].fmeasure,
            "rouge_l": scores["rougeL"].fmeasure,
            "backend": "rouge-score",
        }
    except ImportError:
        overlap = _fallback_overlap(prediction, reference)
        return {
            "rouge_1": overlap,
            "rouge_2": overlap * 0.8,
            "rouge_l": overlap,
            "backend": "fallback",
        }


def bertscore_f1(prediction: str, reference: str) -> dict[str, float]:
    """Compute BERTScore F1 using bert-score when installed."""
    try:
        from bert_score import score as bert_score

        _, _, f1 = bert_score([prediction], [reference], lang="en", verbose=False)
        return {"bertscore_f1": float(f1[0]), "backend": "bert-score"}
    except ImportError:
        overlap = _fallback_overlap(prediction, reference)
        return {"bertscore_f1": overlap, "backend": "fallback"}


def evaluate_generation(prediction: str, reference: str) -> GenerationMetrics:
    rouge = rouge_scores(prediction, reference)
    bert = bertscore_f1(prediction, reference)
    backend = rouge.get("backend", "fallback")
    if bert.get("backend") == "bert-score":
        backend = "rouge-score+bert-score"
    return GenerationMetrics(
        rouge_1=rouge["rouge_1"],
        rouge_2=rouge["rouge_2"],
        rouge_l=rouge["rouge_l"],
        bertscore_f1=bert["bertscore_f1"],
        backend=backend,
        details={"rouge": rouge, "bertscore": bert},
    )
