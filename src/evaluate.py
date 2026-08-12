"""Retrieval scoring.

Primary metric — Hit-in-Top-K: at least one of the top K chunks belongs to a gold
recipe AND covers the gold section. Blind strategy-A windows straddle several
sections, and they are credited for any section they overlap, which is the
generous reading in strategy A's favour.

Secondary metric — Answer-in-Top-K: the retrieved chunk from the gold recipe
actually contains the answer text. A chunk can satisfy the primary metric while
having had the answer row sliced off, and that gap is the whole point of the
comparison.
"""
from typing import Dict, List

from store import query


def judge(hit: Dict, q: Dict):
    meta = hit.get("metadata") or {}
    recipe_ok = meta.get("recipe_id") in q["gold_recipes"]
    covered = meta.get("sections_covered") or f"|{meta.get('section', '')}|"
    section_ok = f"|{q['gold_section']}|" in covered
    marker_ok = any(m in hit["text"] for m in q["markers"])
    return recipe_ok, section_ok, marker_ok


def evaluate_question(collection, q: Dict, k: int = 5) -> Dict:
    hits = query(collection, q["question"], k=k)
    first_hit = None
    first_answer = None
    rows = []
    for h in hits:
        recipe_ok, section_ok, marker_ok = judge(h, q)
        if recipe_ok and section_ok and first_hit is None:
            first_hit = h["rank"]
        if recipe_ok and marker_ok and first_answer is None:
            first_answer = h["rank"]
        rows.append(
            {
                "rank": h["rank"],
                "chunk_id": h["chunk_id"],
                "recipe_id": (h["metadata"] or {}).get("recipe_id", ""),
                "section": (h["metadata"] or {}).get("section", ""),
                "score": h["score"],
                "distance": h["distance"],
                "correct": bool(recipe_ok and section_ok),
                "has_answer": bool(recipe_ok and marker_ok),
                "snippet": " ".join(h["text"].split())[:150],
            }
        )
    return {
        "qid": q["qid"],
        "question": q["question"],
        "type": q["type"],
        "gold_recipes": q["gold_recipes"],
        "gold_section": q["gold_section"],
        "expected_answer": q["answer"],
        "first_hit_rank": first_hit,
        "first_answer_rank": first_answer,
        "hit": first_hit is not None,
        "answer_present": first_answer is not None,
        "results": rows,
    }


def evaluate_strategy(collection, questions: List[Dict], k: int = 5) -> Dict:
    per_q = [evaluate_question(collection, q, k=k) for q in questions]
    return {
        "k": k,
        "hits": sum(1 for r in per_q if r["hit"]),
        "answers": sum(1 for r in per_q if r["answer_present"]),
        "total": len(per_q),
        "per_question": per_q,
    }


def hits_at(per_question: List[Dict], k: int, qids: List[str] = None) -> int:
    """Recompute Hit@k from an existing top-5 run, optionally for a subset."""
    total = 0
    for r in per_question:
        if qids is not None and r["qid"] not in qids:
            continue
        rank = r["first_hit_rank"]
        if rank is not None and rank <= k:
            total += 1
    return total


def answers_at(per_question: List[Dict], k: int, qids: List[str] = None) -> int:
    total = 0
    for r in per_question:
        if qids is not None and r["qid"] not in qids:
            continue
        rank = r["first_answer_rank"]
        if rank is not None and rank <= k:
            total += 1
    return total
