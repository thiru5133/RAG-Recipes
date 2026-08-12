"""Two independent gates against hallucination, plus citation verification."""
from typing import Dict, List

from config import REFUSAL_THRESHOLD
from generate import REFUSAL, extract_citations, generate


def below_threshold(hits: List[Dict], threshold: float = REFUSAL_THRESHOLD) -> bool:
    """Gate 1: nothing retrieved is close enough to be worth an LLM call."""
    return not hits or hits[0]["score"] < threshold


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


def answer_question(question: str, hits: List[Dict], threshold: float = REFUSAL_THRESHOLD) -> Dict:
    """Full guarded path: threshold gate, then prompt gate, then verification."""
    top_score = hits[0]["score"] if hits else None

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
        }

    result = generate(question, hits)
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
    }
