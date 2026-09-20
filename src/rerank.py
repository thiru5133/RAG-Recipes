"""Second-stage rerank over a retrieved candidate pool.

Retrieve a wide first-stage list (semantic, BM25, or hybrid), then rescore
those candidates and fuse the rankings with Reciprocal Rank Fusion.

Signals fused, in order:
1. first-stage rank (the retriever's opinion)
2. BM25 over the candidate texts only, with unit synonyms expanded
   (grams↔g, ml↔millilitre, tbsp↔tablespoon) so table rows can match
3. query-term coverage (how many question tokens appear in the chunk)
4. a section prior when the question type is obvious: quantity → Ingredients,
   nutrition → Nutrition, time/method → Method, substitute → Notes

The refusal gate still reads cosine (`score` / `gate_score`). Rerank only
changes order.
"""
from __future__ import annotations

import re
from typing import Dict, List, Sequence

from rank_bm25 import BM25Okapi

from bm25_search import _tokenise
from config import RERANK_RRF_K

QUANTITY_RE = re.compile(
    r"\b(how many|how much|grams?|ml\b|tablespoons?|teaspoons?|tbsp|tsp)\b",
    re.I,
)
NUTRITION_RE = re.compile(
    r"\b(kcal|calories?|protein|sodium|carbohydrates?|nutrition|fat per)\b",
    re.I,
)
TIME_RE = re.compile(
    r"\b(how long|minutes?|hours?|simmer|bake|preheat|soak|press|sear|boil)\b",
    re.I,
)
SUB_RE = re.compile(
    r"\b(instead|substitut|replace|vegan version|without|alternative)\b",
    re.I,
)

# Preferred section for each question kind. Matching chunks keep first-stage
# order among themselves and sit above every other section.
PREFERRED_SECTION = {
    "quantity": {"Ingredients"},
    "nutrition": {"Nutrition"},
    "time": {"Method"},
    "sub": {"Notes"},
}

# Recipe tables store SI abbreviations; cooks type the full unit.
UNIT_SYNONYMS = {
    "g": ["g", "gram", "grams"],
    "gram": ["g", "gram", "grams"],
    "grams": ["g", "gram", "grams"],
    "ml": ["ml", "millilitre", "milliliter", "millilitres", "milliliters"],
    "millilitre": ["ml"],
    "milliliter": ["ml"],
    "millilitres": ["ml"],
    "milliliters": ["ml"],
    "tbsp": ["tbsp", "tablespoon", "tablespoons"],
    "tablespoon": ["tbsp", "tablespoon", "tablespoons"],
    "tablespoons": ["tbsp", "tablespoon", "tablespoons"],
    "tsp": ["tsp", "teaspoon", "teaspoons"],
    "teaspoon": ["tsp", "teaspoon", "teaspoons"],
    "teaspoons": ["tsp", "teaspoon", "teaspoons"],
    "kcal": ["kcal", "calorie", "calories"],
    "calorie": ["kcal", "calorie", "calories"],
    "calories": ["kcal", "calorie", "calories"],
}


def _question_kind(question: str) -> str | None:
    if NUTRITION_RE.search(question):
        return "nutrition"
    if QUANTITY_RE.search(question):
        return "quantity"
    if SUB_RE.search(question):
        return "sub"
    if TIME_RE.search(question):
        return "time"
    return None


def _expand_tokens(tokens: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for token in tokens:
        for variant in UNIT_SYNONYMS.get(token, [token]):
            if variant not in seen:
                seen.add(variant)
                out.append(variant)
    return out


def _coverage_ranks(question: str, hits: Sequence[Dict]) -> Dict[int, int]:
    q_tokens = _tokenise(question)
    scored = []
    for i, hit in enumerate(hits):
        doc = set(_tokenise(hit.get("text") or ""))
        matched = 0
        for token in q_tokens:
            if any(variant in doc for variant in UNIT_SYNONYMS.get(token, [token])):
                matched += 1
        recall = (matched / len(q_tokens)) if q_tokens else 0.0
        scored.append((recall, i))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return {i: rank for rank, (_, i) in enumerate(scored, start=1)}


def _section_ranks(kind: str, hits: Sequence[Dict]) -> Dict[int, int]:
    preferred = PREFERRED_SECTION[kind]
    matching: List[int] = []
    rest: List[int] = []
    for i, hit in enumerate(hits):
        section = (hit.get("metadata") or {}).get("section") or ""
        (matching if section in preferred else rest).append(i)
    return {idx: rank for rank, idx in enumerate(matching + rest, start=1)}


def rerank(
    question: str, hits: List[Dict], k: int, rrf_k: int = RERANK_RRF_K
) -> List[Dict]:
    """Return the top-k hits after fusing first-stage, BM25, coverage, and section."""
    if not hits:
        return []
    if len(hits) == 1 or k <= 0:
        return hits[:k]

    tokens = _expand_tokens(_tokenise(question))
    corpus = [_tokenise(h.get("text") or "") for h in hits]
    bm25_scores = BM25Okapi(corpus).get_scores(tokens)
    bm25_order = sorted(range(len(hits)), key=lambda i: (-bm25_scores[i], i))
    bm25_rank = {i: rank for rank, i in enumerate(bm25_order, start=1)}
    coverage_rank = _coverage_ranks(question, hits)
    kind = _question_kind(question)
    section_rank = _section_ranks(kind, hits) if kind else None

    fused = []
    for i, hit in enumerate(hits):
        first_rank = int(hit.get("rank") or (i + 1))
        rrf = (
            1.0 / (rrf_k + first_rank)
            + 1.0 / (rrf_k + bm25_rank[i])
            + 1.0 / (rrf_k + coverage_rank[i])
        )
        if section_rank is not None:
            rrf += 1.0 / (rrf_k + section_rank[i])
        fused.append((rrf, i, float(bm25_scores[i]), first_rank))
    fused.sort(key=lambda row: (-row[0], row[3]))

    out: List[Dict] = []
    for new_rank, (rrf, i, bm25_s, first_rank) in enumerate(fused[:k], start=1):
        hit = dict(hits[i])
        hit["retrieve_rank"] = first_rank
        hit["rank"] = new_rank
        hit["rerank_score"] = round(rrf, 4)
        hit["rerank_bm25"] = round(bm25_s, 4)
        out.append(hit)
    return out
