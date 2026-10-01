"""Two independent gates against hallucination, plus citation verification."""
from typing import Dict, List, Optional

from config import REFUSAL_THRESHOLD
from generate import PROMPT_VERSION, REFUSAL, extract_citations, generate


def gate_value(hits: List[Dict]) -> Optional[float]:
    """The number the 0.30 threshold is compared against.

    Semantic and BM25 hits use `score` as before. Hybrid hits carry cosine in
    `gate_score` (the RRF figure is only a ranker). If the RRF-top document was
    BM25-only and has no cosine, the best cosine in the fused window is used so
    the gate still sees the scale it was calibrated on.
    """
    if not hits:
        return None
    top = hits[0].get("gate_score")
    if top is not None:
        return float(top)
    window = [float(h["gate_score"]) for h in hits if h.get("gate_score") is not None]
    if window:
        return max(window)
    return float(hits[0]["score"])


def below_threshold(hits: List[Dict], threshold: float = REFUSAL_THRESHOLD) -> bool:
    """Gate 1: nothing retrieved is close enough to be worth an LLM call."""
    value = gate_value(hits)
    return value is None or value < threshold


def validate_citations(answer: str, hits: List[Dict]) -> Dict:
    """Every cited chunk_id must be one we actually passed in, and its
    recipe_id must match that chunk's real recipe_id."""
    allowed = {h["chunk_id"]: (h.get("metadata") or {}).get("recipe_id") for h in hits}
    cited = extract_citations(answer)
    unknown = [c for c in cited if c[0] not in allowed]
    mismatched = [c for c in cited if c[0] in allowed and allowed[c[0]] != c[1]]
    return {
        "cited": cited,
        "unknown_chunk_ids": unknown,
        "recipe_id_mismatches": mismatched,
        "valid": not unknown and not mismatched and bool(cited),
    }


def answer_question(
    question: str,
    hits: List[Dict],
    threshold: float = REFUSAL_THRESHOLD,
    prompt_version: str = PROMPT_VERSION,
) -> Dict:
    """Full guarded path: threshold gate, then prompt gate, then verification."""
    top_score = gate_value(hits)

    if below_threshold(hits, threshold):
        return {
            "question": question,
            "answer": REFUSAL,
            "refused": True,
            "refused_by": "score_threshold",
            "top_score": top_score,
            "threshold": threshold,
            "citations": None,
            "error": None,
            "generation": None,
        }

    result = generate(question, hits, prompt_version=prompt_version)
    if result["error"]:
        return {
            "question": question,
            "answer": None,
            "refused": False,
            "refused_by": None,
            "top_score": top_score,
            "threshold": threshold,
            "citations": None,
            "error": result["error"],
            "generation": result,
        }

    answer = result["answer"]
    refused = REFUSAL.rstrip(".").lower() in answer.rstrip(".").lower()
    return {
        "question": question,
        "answer": answer,
        "refused": refused,
        "refused_by": "prompt_guard" if refused else None,
        "top_score": top_score,
        "threshold": threshold,
        "citations": None if refused else validate_citations(answer, hits),
        "error": None,
        "generation": result,
    }
